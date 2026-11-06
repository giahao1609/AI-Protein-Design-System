"""Competition Campaign Runner for Changjiang Cup 2026.

Coordinates end-to-end campaign execution for any of the 7 official competition tracks:
1. Target Ingestion: Loads official YAML specification from competition/targets/
2. Engine Selection: Dispatches BindCraft (minibinder) or VHHScaffold (VHH)
3. In Silico Scoring: Evaluates complexes via ESMFold2 + ipSAE (with signal peptide masking)
4. QC & Anti-Collision: Screens 4-scheme CDR uniqueness, Nb35 defense, and developability
5. Persistence & Delivery: Stores in SQLite MetadataStore and exports submission package
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import structlog
import yaml

from protein_design.export.submission import generate_submission_package
from protein_design.generators.base import BaseGenerator
from protein_design.generators.bindcraft import BindCraftGenerator
from protein_design.generators.vhh import VHHScaffoldGenerator
from protein_design.predictors.esmfold_ipsae import ESMFold2_ipSAE_Scorer
from protein_design.schemas import Candidate, CandidateStatus, Target
from protein_design.storage.artifacts import ArtifactStore
from protein_design.storage.database import MetadataStore
from protein_design.validation.druggability import (
    check_druggability,
    verify_anti_collision,
)

log = structlog.get_logger(__name__)


class CompetitionCampaignRunner:
    """Automated campaign orchestrator for Changjiang Cup 2026 targets."""

    def __init__(
        self,
        db: MetadataStore,
        artifacts: ArtifactStore,
        targets_dir: Path | str = "competition/targets",
    ):
        self.db = db
        self.artifacts = artifacts
        self.targets_dir = Path(targets_dir)
        self.scorer = ESMFold2_ipSAE_Scorer(
            num_seeds=1,
            num_samples=1,
            use_templates=False,
            target_msa=True,
            design_msa=False,
        )

    def load_target(self, target_identifier: str | int) -> Target:
        """Load target definition from target ID (e.g. 'EGFR', 'TL1A') or track number (1–7)."""
        search_term = str(target_identifier).lower()
        yaml_files = sorted(self.targets_dir.glob("*.yaml"))

        matched_file: Path | None = None
        for yf in yaml_files:
            if search_term in yf.stem.lower():
                matched_file = yf
                break

        if not matched_file:
            raise FileNotFoundError(
                f"No target YAML found for '{target_identifier}' in {self.targets_dir}"
            )

        with open(matched_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        target = Target.model_validate(data)
        self.db.save_target(target)
        return target

    def select_generator(self, target: Target) -> BaseGenerator:
        """Select appropriate generative engine based on target molecule type."""
        meta = target.metadata or {}
        mol_type = str(meta.get("molecule_type", "")).lower()

        if mol_type in ("minibinder", "binder"):
            return BindCraftGenerator()
        return VHHScaffoldGenerator()

    def run_track_campaign(
        self,
        target_identifier: str | int,
        num_candidates: int = 10,
        mode: Literal["early_claim", "final_optimal"] = "early_claim",
        output_dir: Path | str = "submissions",
        seed: int = 42,
    ) -> dict[str, Any]:
        """Execute end-to-end design, scoring, QC, and package export for a track."""
        target = self.load_target(target_identifier)
        generator = self.select_generator(target)
        meta = target.metadata or {}
        mol_type = meta.get("molecule_type", "minibinder")
        out_path = Path(output_dir)

        log.info(
            "campaign_track_started",
            target_id=target.target_id,
            generator=generator.name,
            molecule_type=mol_type,
            mode=mode,
        )

        # 1. Generate Candidates
        gen_config = {"design_path": str(self.artifacts.base_dir)}
        raw_candidates = generator.generate(
            target=target,
            config=gen_config,
            num_candidates=num_candidates,
            seed=seed,
        )

        clean_tid = target.target_id.lower().replace("-", "").replace("_", "")
        valid_candidates: list[Candidate] = []
        pool_sequences: list[str] = []

        # 2. In Silico Scoring & QC Loop
        for cand in raw_candidates:
            # Ensure candidate_id is uniquely scoped by target to avoid SQLite primary key overwrite
            if not cand.candidate_id.startswith(f"{clean_tid}_"):
                cand.candidate_id = f"{clean_tid}_{cand.candidate_id}"
            cand.target_id = target.target_id

            # Predict complex geometry and ipSAE
            pred_result = self.scorer.predict(cand, target, {})
            cand.metrics.update(pred_result.metrics)

            # Check developability
            assay_ph = 6.0 if "EGFR" in target.target_id.upper() else 7.4
            dev = check_druggability(cand.sequence, molecule_type=mol_type, assay_ph=assay_ph)
            cand.metrics["druggability_passed"] = dev["passed"]

            # Verify anti-collision across pool
            try:
                verify_anti_collision(
                    candidate_seq=cand.sequence,
                    pool_sequences=pool_sequences,
                    molecule_type=mol_type,
                    candidate_id=cand.candidate_id,
                )
                cand.status = CandidateStatus.VALID
                valid_candidates.append(cand)
                pool_sequences.append(cand.sequence)
            except Exception as collision_err:
                cand.status = CandidateStatus.REJECTED
                cand.metadata["rejection_reason"] = str(collision_err)

            # Persist candidate to MetadataStore
            self.db.save_candidate(cand)

        # 3. Sort candidates by ipSAE score descending (best first, handling None safely)
        valid_candidates.sort(
            key=lambda c: float(c.metrics.get("ipsae_score") or 0.0),
            reverse=True,
        )

        # 4. Generate Submission Package
        top_candidates = valid_candidates[:20]
        submission_pkg = generate_submission_package(
            candidates=top_candidates,
            target_name=target.target_id,
            output_dir=out_path,
            molecule_type=mol_type,
            mode=mode,
            db=self.db,
            generate_ascii_fallback=True,
        )

        log.info(
            "campaign_track_completed",
            target_id=target.target_id,
            valid_count=len(valid_candidates),
            submitted_count=len(top_candidates),
            submission_id=submission_pkg["submission_id"],
        )

        return {
            "target_id": target.target_id,
            "generator": generator.name,
            "molecule_type": mol_type,
            "total_generated": len(raw_candidates),
            "valid_candidates": len(valid_candidates),
            "top_candidates": [c.candidate_id for c in top_candidates],
            "submission_package": submission_pkg,
        }
