"""Tier B Integration Tests: BindCraft Generator Contract & Export Safety.

Validates:
1. Strict conformance to frozen BaseGenerator abstract interface
2. Subprocess execution supervisor, timeout handling, and exit code capture
3. End-to-end integration with mock runner generating valid Candidate objects
4. Fail-closed export safety gate separating competition delivery from publication
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from protein_design.core.exceptions import GenerationError, SecurityIntegrityError
from protein_design.export.safety import verify_export_safety
from protein_design.generators.base import BaseGenerator
from protein_design.generators.bindcraft import BindCraftGenerator
from protein_design.generators.dummy import DummyGenerator
from protein_design.schemas import (
    Candidate,
    CandidateStatus,
    DesignType,
    ProvenanceRecord,
    ScientificStatus,
    StatusTransition,
    Target,
)


def test_generator_interface_conformance():
    """Verify BindCraftGenerator adheres to the frozen BaseGenerator contract."""
    generator = BindCraftGenerator()
    assert isinstance(generator, BaseGenerator)
    assert generator.name == "bindcraft"
    assert generator.version == "0.1.0-draft"


def test_mock_pipeline_generation(tmp_path, sample_target):
    """Verify generator.generate() with mock runner returns valid Candidate objects."""
    generator = BindCraftGenerator(
        runner_type="mock",
        mock_output_dir=Path("tests/fixtures/bindcraft_output"),
    )

    config = {
        "params": {
            "output_dir": str(tmp_path / "mock_run"),
            "binder_lengths": [60, 63],
        }
    }

    candidates = generator.generate(
        target=sample_target,
        config=config,
        num_candidates=2,
        seed=42,
    )

    assert len(candidates) == 2
    for cand in candidates:
        assert isinstance(cand, Candidate)
        assert cand.target_id == sample_target.target_id
        assert cand.generator == "bindcraft"
        assert cand.generator_version == "0.1.0-draft"
        assert cand.design_type == DesignType.MINIBINDER
        assert cand.scientific_status == ScientificStatus.GENERATED
        assert len(cand.sequence) > 0
        assert "af2_plddt" in cand.metrics
        assert "pyrosetta_interface_dg" in cand.metrics


def test_subprocess_timeout_isolation(tmp_path, sample_target):
    """Verify subprocess supervisor enforces timeout and terminates child process."""
    generator = BindCraftGenerator(
        runner_type="docker",
        timeout_seconds=1,  # 1-second timeout
    )

    mock_process = MagicMock()
    mock_process.poll.return_value = None  # Never finishes naturally
    mock_process.pid = 99999
    mock_process.wait.side_effect = subprocess.TimeoutExpired(cmd="docker", timeout=10)

    with patch("subprocess.Popen", return_value=mock_process):
        with pytest.raises(GenerationError, match="exceeded timeout"):
            generator.generate(
                target=sample_target,
                config={"params": {"output_dir": str(tmp_path / "timeout_run")}},
                num_candidates=1,
            )

    # Verifies both SIGTERM (terminate) and escalation to SIGKILL (kill) were invoked
    mock_process.terminate.assert_called_once()
    mock_process.kill.assert_called_once()


def test_non_zero_exit_handling(tmp_path, sample_target):
    """Verify container non-zero exit code (e.g. CUDA OOM exit code 137) raises GenerationError."""
    generator = BindCraftGenerator(runner_type="docker")

    mock_process = MagicMock()
    mock_process.poll.return_value = 137  # OOM exit code
    mock_process.communicate.return_value = ("", "CUDA out of memory error in JAX kernel")

    with patch("subprocess.Popen", return_value=mock_process):
        with pytest.raises(GenerationError, match="BindCraft execution failed with exit code 137"):
            generator.generate(
                target=sample_target,
                config={"params": {"output_dir": str(tmp_path / "oom_run")}},
                num_candidates=1,
            )


def test_export_safety_blocks_dummy_generator(tmp_path, sample_target):
    """Verify verify_export_safety unconditionally blocks candidates from dummy generator."""
    dummy_gen = DummyGenerator()
    dummy_cands = dummy_gen.generate(sample_target, config={}, num_candidates=1)
    cand = dummy_cands[0]

    # Even with structure file, generator == 'dummy' is blocked
    dummy_struct = tmp_path / "dummy.cif"
    dummy_struct.write_text("data_cand\n_entry.id test\n")
    cand.structure_path = dummy_struct

    with pytest.raises(SecurityIntegrityError, match="produced by dummy generator"):
        verify_export_safety(cand, purpose="competition")

    with pytest.raises(SecurityIntegrityError, match="produced by dummy generator"):
        verify_export_safety(cand, purpose="publication")


def test_export_safety_blocks_dummy_validated(tmp_path, sample_target):
    """Verify verify_export_safety blocks real candidates that only received dummy validation."""
    real_struct = tmp_path / "real.cif"
    real_struct.write_text("data_cand\n_entry.id test\n")

    cand = Candidate(
        candidate_id="cand_real_001",
        target_id=sample_target.target_id,
        sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLA",
        generator="bindcraft",
        generator_version="0.1.0-draft",
        structure_path=real_struct,
        metadata={"validation_history": ["DummyValidator_v1"]},
    )

    with pytest.raises(SecurityIntegrityError, match="passed only dummy validation"):
        verify_export_safety(cand, purpose="competition")

    # Also test via status_history
    cand2 = Candidate(
        candidate_id="cand_real_002",
        target_id=sample_target.target_id,
        sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLA",
        generator="bindcraft",
        generator_version="0.1.0-draft",
        structure_path=real_struct,
    )
    cand2.status_history.append(
        StatusTransition(
            from_status=CandidateStatus.CREATED,
            to_status=CandidateStatus.VALID,
            reason="Passed dummy validation check",
            stage="dummy_validation",
        )
    )

    with pytest.raises(SecurityIntegrityError, match="passed only dummy validation"):
        verify_export_safety(cand2, purpose="competition")


def test_export_safety_blocks_missing_structure(sample_target):
    """Verify verify_export_safety unconditionally blocks candidates with missing structure coordinates."""
    cand = Candidate(
        candidate_id="cand_nostruct_001",
        target_id=sample_target.target_id,
        sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLA",
        generator="bindcraft",
        generator_version="0.1.0-draft",
        structure_path=None,
    )

    with pytest.raises(SecurityIntegrityError, match="structure coordinate file is missing"):
        verify_export_safety(cand, purpose="competition")


def test_export_safety_purpose_separation(tmp_path, sample_target):
    """Verify purpose separation: competition allows valid non-publication designs, publication mandates publication_ready."""
    real_struct = tmp_path / "valid_binder.cif"
    real_struct.write_text("data_cand\n_entry.id test\n")

    cand = Candidate(
        candidate_id="cand_valid_001",
        target_id=sample_target.target_id,
        sequence="MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLA",
        generator="bindcraft",
        generator_version="0.1.0-draft",
        structure_path=real_struct,
        metadata={"validation_history": ["RosettaFastRelax"]},
    )

    # 1. Competition purpose: PASSES without requiring publication_ready = True
    assert verify_export_safety(cand, purpose="competition") is True

    # 2. Publication purpose: BLOCKED because publication_ready is False/missing
    with pytest.raises(SecurityIntegrityError, match="not marked publication_ready"):
        cand.provenance = ProvenanceRecord(
            run_id="run_test_001",
            target_id=sample_target.target_id,
            generator="bindcraft",
            generator_version="0.1.0-draft",
            config_hash="test_config_hash",
            metadata={"publication_ready": False},
        )
        verify_export_safety(cand, purpose="publication")

    # 3. Publication purpose: PASSES when provenance has publication_ready = True
    cand.provenance.metadata["publication_ready"] = True
    assert verify_export_safety(cand, purpose="publication") is True
