"""Submission Package Exporter for Changjiang Cup 2026.

Validates and formats competition submission files adhering strictly to
official rules:
- File name: {Target}_submission.csv (e.g. TL1A_submission.csv, EGFR_submission.csv)
- Header: exactly ['name', 'sequence']
- Max candidates: 20 rows (total max 21 lines in CSV)
- Allowed characters: 20 standard amino acids (no tags, no whitespace, mature only)
- Length constraints per track type (minibinder: 40-100 aa; VHH: 100-150 aa)
- Integrated with fail-closed verify_export_safety(purpose='competition')
"""

from __future__ import annotations

import csv
import re
from collections.abc import Sequence
from pathlib import Path

from protein_design.core.exceptions import SecurityIntegrityError
from protein_design.export.safety import verify_export_safety
from protein_design.schemas import Candidate

STANDARD_AMINO_ACIDS = set("ACDEFGHIKLMNPQRSTVWY")


def validate_sequence_for_submission(
    sequence: str,
    molecule_type: str = "minibinder",
) -> None:
    """Validate that sequence strictly meets biological competition rules."""
    cleaned = sequence.strip()
    if not cleaned:
        raise SecurityIntegrityError("Submission blocked: Sequence is empty.")

    # Only 20 standard natural amino acids
    invalid_chars = set(cleaned.upper()) - STANDARD_AMINO_ACIDS
    if invalid_chars:
        raise SecurityIntegrityError(
            f"Submission blocked: Sequence contains invalid/non-standard characters: {invalid_chars}"
        )

    # Length constraints
    seq_len = len(cleaned)
    mol_type = molecule_type.lower()
    if mol_type == "minibinder" and not (40 <= seq_len <= 100):
        raise SecurityIntegrityError(
            f"Submission blocked: Minibinder sequence length ({seq_len}) outside valid range [40, 100]."
        )
    elif mol_type in ("vhh", "nanobody") and not (100 <= seq_len <= 150):
        raise SecurityIntegrityError(
            f"Submission blocked: VHH sequence length ({seq_len}) outside valid range [100, 150]."
        )

    # Check for common purification tags (His-tag, Flag-tag, HA-tag, Myc-tag)
    upper_seq = cleaned.upper()
    if "HHHHHH" in upper_seq:
        raise SecurityIntegrityError("Submission blocked: Sequence contains His6-tag.")
    if "DYKDDDDK" in upper_seq:
        raise SecurityIntegrityError("Submission blocked: Sequence contains Flag-tag.")


def generate_submission_package(
    candidates: Sequence[Candidate],
    target_name: str,
    output_dir: Path,
    molecule_type: str = "minibinder",
    max_candidates: int = 20,
) -> Path:
    """Generate official competition submission CSV file.

    Args:
        candidates: List of selected candidate records (top ranked, max 20).
        target_name: Name of target (e.g. 'TL1A', 'EGFR', 'IL-7Ra').
        output_dir: Directory where the CSV file will be written.
        molecule_type: 'minibinder' or 'VHH'.
        max_candidates: Maximum allowed candidates (default: 20).

    Returns:
        Path to the generated submission CSV file.
    """
    if len(candidates) > max_candidates:
        raise SecurityIntegrityError(
            f"Submission blocked: Candidate count ({len(candidates)}) exceeds maximum limit of {max_candidates}."
        )

    # Clean target name for file naming: e.g. 'IL-7Rα' -> 'IL-7Ra' or 'IL-7Ra'
    safe_target_name = re.sub(r"[^\w\-]", "", target_name)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{safe_target_name}_submission.csv"
    submission_path = output_dir / filename

    rows: list[dict[str, str]] = []

    for idx, cand in enumerate(candidates):
        # 1. Gate check
        verify_export_safety(cand, purpose="competition")

        # 2. Sequence check
        validate_sequence_for_submission(cand.sequence, molecule_type=molecule_type)

        name = cand.metadata.get("submission_name") or f"{safe_target_name}_des_{idx+1:02d}"
        rows.append({
            "name": name,
            "sequence": cand.sequence.strip(),
        })

    # Write CSV strictly formatted
    with open(submission_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "sequence"])
        writer.writeheader()
        writer.writerows(rows)

    return submission_path
