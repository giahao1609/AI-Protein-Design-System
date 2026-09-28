"""Failure-injection resilience tests.

Verifies that:
- Individual candidate predictor failures do NOT crash the whole batch
- Individual candidate validator failures mark status correctly
- Timeouts record errors and continue
- Duplicate candidates transition to DUPLICATE without failing batch
"""

import pytest
from protein_design.config.loader import PipelineConfig
from protein_design.core.pipeline import Pipeline
from protein_design.generators.dummy import DummyGenerator
from protein_design.predictors.dummy import DummyPredictor
from protein_design.validation.dummy import DummyValidator
from protein_design.schemas import Target, CandidateStatus, RunStatus
from protein_design.storage.artifacts import ArtifactStore
from protein_design.storage.database import MetadataStore


def test_failure_injection_isolated_errors(tmp_path):
    db = MetadataStore(tmp_path / "fail_test.db")
    db.initialize()
    artifacts = ArtifactStore(tmp_path / "candidates")

    config = PipelineConfig()
    config.generation.num_candidates = 6
    config.generation.random_seed = 42

    # Configure dummy failure injection
    config.prediction.params["fail_candidate_ids"] = ["cand_000002"]
    config.prediction.params["timeout_candidate_ids"] = ["cand_000005"]
    config.validation.params["fail_candidate_ids"] = ["cand_000004"]
    config.generation.params["duplicate_indices"] = [2]  # cand_000003 is duplicate of 1

    target = Target(
        target_id="tgt_fail_001",
        name="Failure Test Target",
        source="unit_test",
        sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLA",
    )

    pipeline = Pipeline(
        config=config,
        generator=DummyGenerator(),
        predictor=DummyPredictor(),
        validator=DummyValidator(),
        db=db,
        artifacts=artifacts,
    )

    run = pipeline.run(target)

    # Batch completed as PARTIAL (some candidates succeeded, some failed/rejected)
    assert run.status == RunStatus.PARTIAL
    assert len(run.errors) >= 3

    # Check candidate statuses
    c1 = db.get_candidate("cand_000001")
    assert c1.status == CandidateStatus.VALID

    c2 = db.get_candidate("cand_000002")
    assert c2.status == CandidateStatus.FAILED  # Predictor failure

    c3 = db.get_candidate("cand_000003")
    assert c3.status == CandidateStatus.DUPLICATE  # Duplicate sequence

    c4 = db.get_candidate("cand_000004")
    assert c4.status == CandidateStatus.FAILED  # Validator failure

    c5 = db.get_candidate("cand_000005")
    assert c5.status == CandidateStatus.FAILED  # Predictor timeout

    c6 = db.get_candidate("cand_000006")
    assert c6.status == CandidateStatus.VALID

    db.close()
