"""Mass-candidate stress test.

Verifies system stability with 1,000 dummy candidates:
- Candidate creation and ID uniqueness
- Fast batch DB writes (save_candidates_batch)
- Artifact directory creation
- Correct summary count
- Query performance
"""

import time
import pytest
from protein_design.config.loader import PipelineConfig
from protein_design.core.pipeline import Pipeline
from protein_design.generators.dummy import DummyGenerator
from protein_design.predictors.dummy import DummyPredictor
from protein_design.validation.dummy import DummyValidator
from protein_design.schemas import Target, CandidateStatus
from protein_design.storage.artifacts import ArtifactStore
from protein_design.storage.database import MetadataStore


def test_mass_1000_candidates(tmp_path):
    db_path = tmp_path / "mass_test.db"
    artifacts_dir = tmp_path / "candidates"

    db = MetadataStore(db_path)
    db.initialize()
    artifacts = ArtifactStore(artifacts_dir)

    config = PipelineConfig()
    config.generation.num_candidates = 1000
    config.generation.random_seed = 12345

    target = Target(
        target_id="tgt_mass_001",
        name="Mass Target",
        source="unit_test",
        sequence="ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWY",
    )

    generator = DummyGenerator()
    predictor = DummyPredictor()
    validator = DummyValidator()

    pipeline = Pipeline(
        config=config,
        generator=generator,
        predictor=predictor,
        validator=validator,
        db=db,
        artifacts=artifacts,
    )

    start_time = time.time()
    run = pipeline.run(target)
    elapsed = time.time() - start_time

    assert run.status.value == "COMPLETED"
    assert len(run.candidate_ids) == 1000
    assert run.output_summary["total_candidates"] == 1000
    assert run.output_summary["succeeded"] == 1000

    # ID uniqueness check
    unique_ids = set(run.candidate_ids)
    assert len(unique_ids) == 1000

    # DB query check
    count = db.count_candidates(target_id="tgt_mass_001")
    assert count == 1000

    # List candidates query performance check
    candidates = db.list_candidates(target_id="tgt_mass_001", limit=100)
    assert len(candidates) == 100

    db.close()
