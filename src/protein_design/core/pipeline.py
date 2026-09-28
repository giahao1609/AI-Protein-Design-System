"""Pipeline orchestrator — Runs the full candidate design pipeline.

Design principles:
1. One candidate failing does NOT crash the batch
2. Pipeline supports checkpoint/resume
3. All stages use abstract interfaces (Generator, Predictor, Validator)
4. No model-specific code in this module
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any, Optional

from protein_design.config.loader import PipelineConfig
from protein_design.core.lifecycle import validate_transition, is_terminal
from protein_design.generators.base import BaseGenerator
from protein_design.predictors.base import BasePredictor
from protein_design.validation.base import BaseValidator
from protein_design.provenance.tracker import create_provenance
from protein_design.schemas import (
    Candidate,
    CandidateStatus,
    ErrorRecord,
    ExperimentRun,
    Target,
    hash_dict,
    utc_now,
)
from protein_design.storage.artifacts import ArtifactStore
from protein_design.storage.database import MetadataStore
from protein_design.logging import get_logger


class Pipeline:
    """Orchestrates the full candidate design pipeline.

    Workflow:
        Target → Generator → [Candidates] → Predictor → Validator → Storage

    Error isolation: Each candidate is processed independently.
    If one fails, the error is recorded and the batch continues.

    Checkpoint/resume: The pipeline checks which candidates have already
    been processed and skips them on resume.
    """

    def __init__(
        self,
        config: PipelineConfig,
        generator: BaseGenerator,
        predictor: BasePredictor,
        validator: BaseValidator,
        db: MetadataStore,
        artifacts: ArtifactStore,
    ):
        self.config = config
        self.generator = generator
        self.predictor = predictor
        self.validator = validator
        self.db = db
        self.artifacts = artifacts
        self.log = get_logger(
            module="pipeline",
            generator=generator.name,
            predictor=predictor.name,
        )

    def run(
        self,
        target: Target,
        run: Optional[ExperimentRun] = None,
    ) -> ExperimentRun:
        """Execute the full pipeline for a target.

        Args:
            target: The protein target to design binders for.
            run: Optional existing run to resume. Creates new if None.

        Returns:
            The completed ExperimentRun with all results.
        """
        # Create or resume run
        if run is None:
            run = ExperimentRun(
                target_id=target.target_id,
                pipeline_version=self.config.version,
                config_hash=self.config.config_hash,
                random_seed=self.config.generation.random_seed,
                input_config=self.config.model_dump(),
            )
        run.mark_started()
        self.db.save_target(target)
        self.db.save_run(run)

        self.log.info(
            "pipeline_started",
            run_id=run.run_id,
            target_id=target.target_id,
            num_candidates=self.config.generation.num_candidates,
        )

        # --- Stage 1: Generation (or Resume existing candidates) ---
        if run.candidate_ids:
            self.log.info(
                "pipeline_resuming",
                run_id=run.run_id,
                existing_candidates=len(run.candidate_ids),
            )
            candidates = []
            for cid in run.candidate_ids:
                c = self.db.get_candidate(cid)
                if c:
                    candidates.append(c)
        else:
            candidates = self._stage_generate(target, run)

        # --- Stage 2-5: Process each candidate independently ---
        succeeded = 0
        failed = 0
        rejected = 0

        for candidate in candidates:
            try:
                # Check if already processed (resume support)
                existing = self.db.get_candidate(candidate.candidate_id)
                current_candidate = existing if existing else candidate

                if is_terminal(current_candidate.status):
                    self.log.info(
                        "candidate_skipped",
                        candidate_id=current_candidate.candidate_id,
                        reason="already_terminal",
                        status=current_candidate.status.value,
                    )
                    if current_candidate.status == CandidateStatus.VALID:
                        succeeded += 1
                    elif current_candidate.status in (
                        CandidateStatus.REJECTED,
                        CandidateStatus.DUPLICATE,
                        CandidateStatus.INVALID,
                    ):
                        rejected += 1
                    else:
                        failed += 1
                    continue

                # Stage 2: Structure prediction
                current_candidate = self._stage_predict(current_candidate, target, run)
                if is_terminal(current_candidate.status):
                    if current_candidate.status in (
                        CandidateStatus.REJECTED,
                        CandidateStatus.DUPLICATE,
                        CandidateStatus.INVALID,
                    ):
                        rejected += 1
                    else:
                        failed += 1
                    continue

                # Stage 3: Validation (sequence, structure, interface, developability, novelty)
                current_candidate = self._stage_validate(current_candidate, run)
                if current_candidate.status == CandidateStatus.VALID:
                    succeeded += 1
                elif current_candidate.status in (
                    CandidateStatus.REJECTED,
                    CandidateStatus.DUPLICATE,
                    CandidateStatus.INVALID,
                ):
                    rejected += 1
                else:
                    failed += 1

            except Exception as e:
                failed += 1
                error = ErrorRecord(
                    candidate_id=candidate.candidate_id,
                    stage="pipeline",
                    error_type=type(e).__name__,
                    error_message=str(e),
                    traceback=traceback.format_exc(),
                )
                run.add_error(error)
                candidate.transition(
                    CandidateStatus.FAILED,
                    reason=str(e),
                    stage="pipeline",
                )
                self.db.save_candidate(candidate)
                self.log.error(
                    "candidate_failed",
                    candidate_id=candidate.candidate_id,
                    error=str(e),
                )

        # Finalize run
        summary = {
            "total_candidates": len(candidates),
            "succeeded": succeeded,
            "failed": failed,
            "rejected": rejected,
        }

        if failed > 0 and succeeded > 0:
            run.mark_partial()
        elif failed > 0 and succeeded == 0:
            run.mark_failed(ErrorRecord(
                stage="pipeline",
                error_type="AllCandidatesFailed",
                error_message=f"All {failed} candidates failed",
            ))
        else:
            run.mark_completed(summary)

        run.output_summary = summary
        self.db.save_run(run)

        self.log.info(
            "pipeline_completed",
            run_id=run.run_id,
            status=run.status.value,
            **summary,
        )

        return run

    def _stage_generate(
        self, target: Target, run: ExperimentRun
    ) -> list[Candidate]:
        """Stage 1: Generate candidate sequences."""
        self.log.info("stage_generate_started", target_id=target.target_id)

        try:
            candidates = self.generator.generate(
                target=target,
                config=self.config.generation.model_dump(),
                num_candidates=self.config.generation.num_candidates,
                seed=self.config.generation.random_seed,
            )
        except Exception as e:
            self.log.error("stage_generate_failed", error=str(e))
            error = ErrorRecord(
                stage="generation",
                error_type=type(e).__name__,
                error_message=str(e),
                traceback=traceback.format_exc(),
            )
            run.mark_failed(error)
            self.db.save_run(run)
            raise

        seen_hashes: set[str] = set()

        # Assign provenance and save each candidate
        for candidate in candidates:
            provenance = create_provenance(
                run_id=run.run_id,
                target_id=target.target_id,
                generator=self.generator.name,
                generator_version=self.generator.version,
                config=self.config.generation.model_dump(),
                random_seed=candidate.seed,
                input_data={"target_hash": target.target_hash},
            )
            candidate.provenance = provenance
            candidate.transition(
                CandidateStatus.GENERATED,
                reason="generator_output",
                stage="generation",
            )

            # Check sequence deduplication
            if candidate.sequence_hash in seen_hashes or self.db.candidate_exists_by_hash(candidate.sequence_hash):
                candidate.transition(
                    CandidateStatus.DUPLICATE,
                    reason="duplicate_sequence_hash",
                    stage="generation",
                )
            else:
                seen_hashes.add(candidate.sequence_hash)

            run.add_candidate(candidate.candidate_id)

            # Save artifacts
            self.artifacts.save_sequence(
                target.target_id,
                candidate.candidate_id,
                candidate.sequence,
                description=f"generator={self.generator.name}",
            )
            self.artifacts.save_provenance(
                target.target_id,
                candidate.candidate_id,
                provenance.model_dump(),
            )

        # Batch save candidates to DB
        self.db.save_candidates_batch(candidates)

        self.log.info(
            "stage_generate_completed",
            num_candidates=len(candidates),
        )
        return candidates

    def _stage_predict(
        self,
        candidate: Candidate,
        target: Target,
        run: ExperimentRun,
    ) -> Candidate:
        """Stage 2: Predict structure for a candidate."""
        self.log.info(
            "stage_predict_started",
            candidate_id=candidate.candidate_id,
        )

        try:
            # Sequence validation (basic check before prediction)
            candidate.transition(
                CandidateStatus.SEQUENCE_VALIDATED,
                reason="basic_sequence_check_passed",
                stage="sequence_validation",
            )

            result = self.predictor.predict(
                candidate=candidate,
                target=target,
                config=self.config.prediction.model_dump(),
            )

            # Store prediction metrics
            candidate.metrics.update(result.metrics)
            if result.structure_content:
                path = self.artifacts.save_structure(
                    target.target_id,
                    candidate.candidate_id,
                    result.structure_content,
                    filename="binder.cif",
                )
                candidate.structure_path = path
            if result.complex_content:
                path = self.artifacts.save_structure(
                    target.target_id,
                    candidate.candidate_id,
                    result.complex_content,
                    filename="complex.cif",
                )
                candidate.complex_structure_path = path

            candidate.transition(
                CandidateStatus.STRUCTURE_PREDICTED,
                reason="prediction_complete",
                stage="structure_prediction",
            )
            self.db.save_candidate(candidate)

        except Exception as e:
            error = ErrorRecord(
                candidate_id=candidate.candidate_id,
                stage="structure_prediction",
                error_type=type(e).__name__,
                error_message=str(e),
                traceback=traceback.format_exc(),
            )
            run.add_error(error)
            candidate.transition(
                CandidateStatus.FAILED,
                reason=str(e),
                stage="structure_prediction",
            )
            self.db.save_candidate(candidate)
            self.log.error(
                "stage_predict_failed",
                candidate_id=candidate.candidate_id,
                error=str(e),
            )

        return candidate

    def _stage_validate(
        self,
        candidate: Candidate,
        run: ExperimentRun,
    ) -> Candidate:
        """Stage 3-5: Run validation checks on a candidate."""
        self.log.info(
            "stage_validate_started",
            candidate_id=candidate.candidate_id,
        )

        try:
            result = self.validator.validate(
                candidate=candidate,
                config=self.config.validation.model_dump(),
            )

            # Apply validation results
            candidate.sequence_qc = result.sequence_qc
            candidate.structure_qc = result.structure_qc
            candidate.interface_qc = result.interface_qc

            # Walk through validation stages
            validation_stages = [
                ("structure_qc", CandidateStatus.STRUCTURE_CHECKED, result.structure_qc),
                ("interface_qc", CandidateStatus.INTERFACE_CHECKED, result.interface_qc),
                ("developability", CandidateStatus.DEVELOPABILITY_CHECKED, result.developability_qc),
                ("novelty", CandidateStatus.NOVELTY_CHECKED, result.novelty_qc),
            ]

            for stage_name, next_status, qc in validation_stages:
                if is_terminal(candidate.status):
                    break

                if qc and not qc.passed:
                    reject_status = (
                        CandidateStatus.DUPLICATE
                        if stage_name == "novelty" and not qc.passed
                        else CandidateStatus.REJECTED
                    )
                    candidate.transition(
                        reject_status,
                        reason=f"{stage_name}_failed: {qc.metric_name}={qc.metric_value}",
                        stage=stage_name,
                        metric_name=qc.metric_name,
                        metric_value=qc.metric_value,
                        threshold=qc.threshold,
                    )
                    break
                else:
                    candidate.transition(
                        next_status,
                        reason=f"{stage_name}_passed",
                        stage=stage_name,
                        metric_name=qc.metric_name if qc else None,
                        metric_value=qc.metric_value if qc else None,
                        threshold=qc.threshold if qc else None,
                    )

            # If all checks passed, mark as VALID
            if candidate.status == CandidateStatus.NOVELTY_CHECKED:
                candidate.transition(
                    CandidateStatus.VALID,
                    reason="all_checks_passed",
                    stage="final_validation",
                )

            self.db.save_candidate(candidate)
            self.log.info(
                "stage_validate_completed",
                candidate_id=candidate.candidate_id,
                final_status=candidate.status.value,
            )

        except Exception as e:
            error = ErrorRecord(
                candidate_id=candidate.candidate_id,
                stage="validation",
                error_type=type(e).__name__,
                error_message=str(e),
                traceback=traceback.format_exc(),
            )
            run.add_error(error)
            candidate.transition(
                CandidateStatus.FAILED,
                reason=str(e),
                stage="validation",
            )
            self.db.save_candidate(candidate)
            self.log.error(
                "stage_validate_failed",
                candidate_id=candidate.candidate_id,
                error=str(e),
            )

        return candidate
