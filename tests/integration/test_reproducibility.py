"""Reproducibility integration test.

Verifies that running the pipeline twice with identical target, config,
and random seed produces deterministic results.
"""

import pytest
from protein_design.config.loader import PipelineConfig
from protein_design.core.pipeline import Pipeline
from protein_design.generators.dummy import DummyGenerator
from protein_design.predictors.dummy import DummyPredictor
from protein_design.validation.dummy import DummyValidator
from protein_design.schemas import Target
from protein_design.storage.artifacts import ArtifactStore
from protein_design.storage.database import MetadataStore


def test_deterministic_pipeline_execution(tmp_path):
    target = Target(
        target_id="tgt_repro_001",
        name="Reproducibility Target",
        source="unit_test",
        sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLA",
    )

    # Run 1
    db1 = MetadataStore(tmp_path / "repro1.db")
    db1.initialize()
    artifacts1 = ArtifactStore(tmp_path / "cand1")

    config1 = PipelineConfig()
    config1.generation.num_candidates = 5
    config1.generation.random_seed = 777

    pipeline1 = Pipeline(
        config=config1,
        generator=DummyGenerator(),
        predictor=DummyPredictor(),
        validator=DummyValidator(),
        db=db1,
        artifacts=artifacts1,
    )
    run1 = pipeline1.run(target)
    cands1 = db1.list_candidates(target_id="tgt_repro_001")

    # Run 2
    db2 = MetadataStore(tmp_path / "repro2.db")
    db2.initialize()
    artifacts2 = ArtifactStore(tmp_path / "cand2")

    config2 = PipelineConfig()
    config2.generation.num_candidates = 5
    config2.generation.random_seed = 777

    pipeline2 = Pipeline(
        config=config2,
        generator=DummyGenerator(),
        predictor=DummyPredictor(),
        validator=DummyValidator(),
        db=db2,
        artifacts=artifacts2,
    )
    run2 = pipeline2.run(target)
    cands2 = db2.list_candidates(target_id="tgt_repro_001")

    # Verify identical sequences, metrics, and statuses
    assert len(cands1) == len(cands2) == 5
    for c1, c2 in zip(cands1, cands2):
        assert c1.sequence == c2.sequence
        assert c1.length == c2.length
        assert c1.metrics == c2.metrics
        assert c1.status == c2.status

    db1.close()
    db2.close()
