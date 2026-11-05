"""Pytest configuration and shared fixtures."""

from __future__ import annotations

from collections.abc import Generator

import pytest

from protein_design.config.loader import PipelineConfig
from protein_design.schemas import Candidate, Target
from protein_design.schemas.common import (
    DesignType,
)
from protein_design.storage.artifacts import ArtifactStore
from protein_design.storage.database import MetadataStore


@pytest.fixture
def tmp_dir(tmp_path):
    """Provide a temporary directory."""
    return tmp_path


@pytest.fixture
def db(tmp_path) -> Generator[MetadataStore, None, None]:
    """Provide an initialized in-memory-like SQLite database."""
    db_path = tmp_path / "test.db"
    store = MetadataStore(db_path)
    store.initialize()
    yield store
    store.close()


@pytest.fixture
def artifacts(tmp_path) -> ArtifactStore:
    """Provide a temporary artifact store."""
    return ArtifactStore(tmp_path / "candidates")


@pytest.fixture
def sample_target() -> Target:
    """Create a sample target for testing."""
    return Target(
        target_id="test_target_001",
        name="Test Target",
        source="test",
        sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLA",
        source_references=["test_reference"],
    )


@pytest.fixture
def sample_candidate(sample_target) -> Candidate:
    """Create a sample candidate for testing."""
    return Candidate(
        candidate_id="test_cand_001",
        target_id=sample_target.target_id,
        sequence="ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWY",
        design_type=DesignType.MINIBINDER,
        generator="test_generator",
        generator_version="1.0.0",
        seed=42,
    )


@pytest.fixture
def config() -> PipelineConfig:
    """Provide a default test configuration."""
    return PipelineConfig()
