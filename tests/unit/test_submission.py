"""Unit tests for competition submission package export."""

from __future__ import annotations

import csv

import pytest

from protein_design.core.exceptions import SecurityIntegrityError
from protein_design.export.submission import (
    generate_submission_package,
    validate_sequence_for_submission,
)
from protein_design.schemas import Candidate


def test_validate_sequence_rules():
    """Verify sequence validation for amino acids and length."""
    # Valid minibinder (60 aa)
    valid_seq = "ACDEFGHIKLMNPQRSTVWY" * 3
    validate_sequence_for_submission(valid_seq, molecule_type="minibinder")

    # Invalid character (e.g. 'B' or 'X')
    with pytest.raises(SecurityIntegrityError, match="invalid/non-standard characters"):
        validate_sequence_for_submission("ACDEFGHIKLMNPQRSTVWX" * 3, molecule_type="minibinder")

    # Length violation (minibinder < 40)
    with pytest.raises(SecurityIntegrityError, match="outside valid range"):
        validate_sequence_for_submission("ACDEFGHIKLMNPQRSTVWY", molecule_type="minibinder")

    # Purification tag (His-tag)
    with pytest.raises(SecurityIntegrityError, match="His6-tag"):
        validate_sequence_for_submission(
            "HHHHHH" + "ACDEFGHIKLMNPQRSTVWY" * 2, molecule_type="minibinder"
        )


def test_generate_submission_package_format(tmp_path):
    """Verify submission CSV has exact header, naming, and content."""
    real_struct = tmp_path / "structure.cif"
    real_struct.write_text("data_test\n_entry.id 1\n")

    seq = "ACDEFGHIKLMNPQRSTVWY" * 3  # 60 aa
    candidates = [
        Candidate(
            candidate_id=f"cand_{i+1:03d}",
            target_id="TL1A",
            sequence=seq,
            generator="bindcraft",
            generator_version="0.1.0-draft",
            structure_path=real_struct,
            metadata={"validation_history": ["RosettaFastRelax"]},
        )
        for i in range(5)
    ]

    out_file = generate_submission_package(
        candidates=candidates,
        target_name="TL1A",
        output_dir=tmp_path / "submissions",
        molecule_type="minibinder",
    )

    assert out_file.name == "TL1A_submission.csv"
    assert out_file.exists()

    with open(out_file, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == ["name", "sequence"]
        rows = list(reader)
        assert len(rows) == 5
        assert rows[0][0] == "TL1A_des_01"
        assert rows[0][1] == seq


def test_generate_submission_package_exceeds_max(tmp_path):
    """Verify submission blocks if candidate count > 20."""
    real_struct = tmp_path / "structure.cif"
    real_struct.write_text("data_test\n_entry.id 1\n")

    seq = "ACDEFGHIKLMNPQRSTVWY" * 3
    candidates = [
        Candidate(
            candidate_id=f"cand_{i+1:03d}",
            target_id="TL1A",
            sequence=seq,
            generator="bindcraft",
            generator_version="0.1.0-draft",
            structure_path=real_struct,
            metadata={"validation_history": ["RosettaFastRelax"]},
        )
        for i in range(25)
    ]

    with pytest.raises(SecurityIntegrityError, match="exceeds maximum limit"):
        generate_submission_package(
            candidates=candidates,
            target_name="TL1A",
            output_dir=tmp_path / "submissions",
            molecule_type="minibinder",
            max_candidates=20,
        )
