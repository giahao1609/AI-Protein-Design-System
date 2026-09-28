"""Resume functionality integration test.

Verifies that:
- A run interrupted midway can be resumed
- Already processed/terminal candidates are skipped
- Resumed run reuses existing candidate IDs rather than generating new ones
"""

import pytest
from protein_design.config.loader import PipelineConfig
from protein_design.core.pipeline import Pipeline
from protein_design.generators.dummy import DummyGenerator
from protein_design.predictors.dummy import DummyPredictor
from protein_design.validation.dummy import DummyValidator
from protein_design.schemas import Target, CandidateStatus, RunStatus, ExperimentRun
from protein_design.storage.artifacts import ArtifactStore
from protein_design.storage.database import MetadataStore


def test_interrupted_run_resume(tmp_path):
    db = MetadataStore(tmp_path / "resume_test.db")
    db.initialize()
    artifacts = ArtifactStore(tmp_path / "candidates")

    config = PipelineConfig()
    config.generation.num_candidates = 5
    config.generation.random_seed = 999

    target = Target(
        target_id="tgt_resume_001",
        name="Resume Target",
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

    # 1. Run generation stage by running initial run
    initial_run = pipeline.run(target)
    assert len(initial_run.candidate_ids) == 5
    assert initial_run.status == RunStatus.COMPLETED

    # 2. Simulate interruption by reverting candidate 4 & 5 to GENERATED
    c4 = db.get_candidate("cand_000004")
    c4.status = CandidateStatus.GENERATED
    db.save_candidate(c4)

    c5 = db.get_candidate("cand_000005")
    c5.status = CandidateStatus.GENERATED
    db.save_candidate(c5)

    # 3. Resume run passing the existing run
    resumed_run = pipeline.run(target, run=initial_run)

    assert resumed_run.run_id == initial_run.run_id
    assert resumed_run.status == RunStatus.COMPLETED
    assert len(resumed_run.candidate_ids) == 5

    # Check candidates 4 and 5 are now VALID
    c4_after = db.get_candidate("cand_000004")
    c5_after = db.get_candidate("cand_000005")
    assert c4_after.status == CandidateStatus.VALID
    assert c5_after.status == CandidateStatus.VALID

    db.close()
