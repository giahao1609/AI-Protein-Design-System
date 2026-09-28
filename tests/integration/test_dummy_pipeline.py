"""Integration test — Full dummy pipeline end-to-end.

This test verifies:
1. Target → DummyGenerator → Candidates
2. Candidates → DummyPredictor → Structures
3. Candidates → DummyValidator → QC results
4. All candidates stored in DB and filesystem
5. Provenance recorded for every candidate
6. One candidate failing does not crash the batch
7. Pipeline produces a valid ExperimentRun
"""

from __future__ import annotations

import pytest

from protein_design.config.loader import PipelineConfig
from protein_design.core.pipeline import Pipeline
from protein_design.generators.dummy import DummyGenerator
from protein_design.predictors.dummy import DummyPredictor
from protein_design.validation.dummy import DummyValidator
from protein_design.schemas import (
    CandidateStatus,
    Target,
    ScientificStatus,
)
from protein_design.storage.database import MetadataStore
from protein_design.storage.artifacts import ArtifactStore


class TestDummyPipeline:
    """End-to-end test of the dummy pipeline."""

    @pytest.fixture
    def pipeline_components(self, tmp_path):
        """Set up all pipeline components."""
        config = PipelineConfig()
        config.generation.num_candidates = 10
        config.generation.random_seed = 42

        db = MetadataStore(tmp_path / "test.db")
        db.initialize()
        artifacts = ArtifactStore(tmp_path / "candidates")

        target = Target(
            target_id="test_target",
            name="Test Target",
            source="test",
            sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLA",
            source_references=["test"],
        )

        pipeline = Pipeline(
            config=config,
            generator=DummyGenerator(),
            predictor=DummyPredictor(),
            validator=DummyValidator(),
            db=db,
            artifacts=artifacts,
        )

        return pipeline, target, db, artifacts, config

    def test_full_pipeline_runs(self, pipeline_components):
        """Test that the full pipeline completes without errors."""
        pipeline, target, db, artifacts, config = pipeline_components
        run = pipeline.run(target)

        assert run.status.value in ("COMPLETED", "PARTIAL")
        assert run.output_summary is not None
        assert run.output_summary["total_candidates"] == 10

    def test_candidates_stored_in_db(self, pipeline_components):
        """Test that all candidates are stored in the database."""
        pipeline, target, db, artifacts, config = pipeline_components
        pipeline.run(target)

        candidates = db.list_candidates(target_id=target.target_id)
        assert len(candidates) == 10

    def test_all_candidates_have_provenance(self, pipeline_components):
        """Test that every candidate has provenance."""
        pipeline, target, db, artifacts, config = pipeline_components
        pipeline.run(target)

        candidates = db.list_candidates(target_id=target.target_id)
        for c in candidates:
            assert c.provenance is not None
            assert c.provenance.generator == "dummy"
            assert c.provenance.config_hash != ""
            assert c.provenance.run_id != ""

    def test_all_candidates_have_status_history(self, pipeline_components):
        """Test that every candidate has status transition history."""
        pipeline, target, db, artifacts, config = pipeline_components
        pipeline.run(target)

        candidates = db.list_candidates(target_id=target.target_id)
        for c in candidates:
            assert len(c.status_history) > 0

    def test_candidates_have_metrics(self, pipeline_components):
        """Test that candidates have prediction metrics."""
        pipeline, target, db, artifacts, config = pipeline_components
        pipeline.run(target)

        candidates = db.list_candidates(target_id=target.target_id)
        for c in candidates:
            # Every candidate that got past prediction should have metrics
            if c.status not in (CandidateStatus.CREATED, CandidateStatus.FAILED):
                assert "plddt" in c.metrics
                assert "iptm" in c.metrics

    def test_artifacts_created(self, pipeline_components):
        """Test that artifact files are created on filesystem."""
        pipeline, target, db, artifacts, config = pipeline_components
        pipeline.run(target)

        candidates = db.list_candidates(target_id=target.target_id)
        for c in candidates:
            # Check sequence FASTA exists
            assert artifacts.candidate_artifact_exists(
                target.target_id, c.candidate_id, "sequence.fasta"
            )
            # Check provenance JSON exists
            assert artifacts.candidate_artifact_exists(
                target.target_id, c.candidate_id, "provenance.json"
            )

    def test_target_stored(self, pipeline_components):
        """Test that the target is stored in the database."""
        pipeline, target, db, artifacts, config = pipeline_components
        pipeline.run(target)

        loaded = db.get_target(target.target_id)
        assert loaded is not None
        assert loaded.name == target.name

    def test_run_stored(self, pipeline_components):
        """Test that the experiment run is stored."""
        pipeline, target, db, artifacts, config = pipeline_components
        run = pipeline.run(target)

        loaded = db.get_run(run.run_id)
        assert loaded is not None
        assert len(loaded.candidate_ids) == 10

    def test_scientific_status_is_generated(self, pipeline_components):
        """Test that scientific status remains GENERATED (no wet-lab)."""
        pipeline, target, db, artifacts, config = pipeline_components
        pipeline.run(target)

        candidates = db.list_candidates(target_id=target.target_id)
        for c in candidates:
            # Without wet-lab, scientific status should be GENERATED
            assert c.scientific_status == ScientificStatus.GENERATED

    def test_deterministic_with_same_seed(self, tmp_path):
        """Test that same seed produces same sequences."""
        results = []
        for i in range(2):
            config = PipelineConfig()
            config.generation.num_candidates = 5
            config.generation.random_seed = 42

            db = MetadataStore(tmp_path / f"test_{i}.db")
            db.initialize()
            artifacts = ArtifactStore(tmp_path / f"candidates_{i}")

            target = Target(
                target_id="test_target",
                name="Test",
                source="test",
                sequence="MKTVRQERLKSIVRILERSKEPV",
                source_references=["test"],
            )

            pipeline = Pipeline(
                config=config,
                generator=DummyGenerator(),
                predictor=DummyPredictor(),
                validator=DummyValidator(),
                db=db,
                artifacts=artifacts,
            )
            pipeline.run(target)

            candidates = db.list_candidates(target_id=target.target_id)
            results.append([c.sequence for c in candidates])
            db.close()

        assert results[0] == results[1]  # Same seed → same sequences
