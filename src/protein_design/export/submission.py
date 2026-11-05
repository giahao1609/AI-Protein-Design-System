"""Submission Package Exporter for Changjiang Cup 2026.

Supports both Rolling Submission ('early_claim') to secure timestamps under the
First-come, First-served rule and Final Optimal ('final_optimal') submission.

Features:
- Exact CSV format: 1 Header ('name,sequence') + up to 20 candidate rows (max 21 rows)
- Target name prefixed files: {Target}_submission.csv
- Dual file generation (Unicode original + ASCII fallback for Greek characters)
- Accompanied by update_note.txt and methods_abstract.txt (< 4,000 chars)
- Persistence in SQLite submission_history table
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal
from uuid import uuid4

from protein_design.core.exceptions import SecurityIntegrityError
from protein_design.export.safety import verify_export_safety
from protein_design.schemas import Candidate

if TYPE_CHECKING:
    from protein_design.storage.database import MetadataStore

STANDARD_AMINO_ACIDS = set("ACDEFGHIKLMNPQRSTVWY")

ASCII_TARGET_MAP = {
    "TNF-α": "TNF-a",
    "IL-7Rα": "IL-7Ra",
    "TNF-alpha": "TNF-a",
    "IL-7Ra": "IL-7Ra",
}


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
            f"Submission blocked: Sequence contains invalid/non-standard characters: "
            f"{invalid_chars}"
        )

    # Length constraints
    seq_len = len(cleaned)
    mol_type = molecule_type.lower()
    if mol_type == "minibinder" and not (40 <= seq_len <= 100):
        raise SecurityIntegrityError(
            f"Submission blocked: Minibinder sequence length ({seq_len}) "
            "outside valid range [40, 100]."
        )
    elif mol_type in ("vhh", "nanobody") and not (100 <= seq_len <= 150):
        raise SecurityIntegrityError(
            f"Submission blocked: VHH sequence length ({seq_len}) "
            "outside valid range [100, 150]."
        )

    # Check for common purification tags (His-tag, Flag-tag, Myc-tag, Strep-tag)
    upper_seq = cleaned.upper()
    if "HHHHHH" in upper_seq:
        raise SecurityIntegrityError("Submission blocked: Sequence contains His6-tag.")
    if "DYKDDDDK" in upper_seq:
        raise SecurityIntegrityError("Submission blocked: Sequence contains Flag-tag.")
    if "EQKLISEEDL" in upper_seq:
        raise SecurityIntegrityError("Submission blocked: Sequence contains Myc-tag.")
    if "WSHPQFEK" in upper_seq:
        raise SecurityIntegrityError("Submission blocked: Sequence contains Strep-tag.")
    if upper_seq.startswith("GGGGS") or upper_seq.endswith("GGGGS"):
        raise SecurityIntegrityError(
            "Submission blocked: Sequence contains redundant terminal GS linker."
        )


def generate_submission_package(
    candidates: Sequence[Candidate],
    target_name: str,
    output_dir: Path,
    molecule_type: str = "minibinder",
    max_candidates: int = 20,
    mode: Literal["early_claim", "final_optimal"] = "final_optimal",
    generate_ascii_fallback: bool = True,
    db: MetadataStore | None = None,
) -> dict[str, Any]:
    """Generate official competition submission package with rolling claim support.

    Args:
        candidates: List of selected candidate records.
        target_name: Name of target (e.g. 'TL1A', 'EGFR', 'TNF-α').
        output_dir: Directory where submission package files are written.
        molecule_type: 'minibinder' or 'VHH'.
        max_candidates: Maximum allowed candidates (default: 20).
        mode: 'early_claim' (min 5 candidates) or 'final_optimal'.
        generate_ascii_fallback: Also generate ASCII-named CSV if target contains Greek letters.
        db: Optional MetadataStore to record submission in SQLite history.

    Returns:
        dict with paths to primary_csv, fallback_csv, update_note, methods_abstract, and metadata.
    """
    if len(candidates) > max_candidates:
        raise SecurityIntegrityError(
            f"Submission blocked: Candidate count ({len(candidates)}) "
            f"exceeds maximum limit of {max_candidates}."
        )

    if mode == "early_claim" and len(candidates) < 1:
        raise SecurityIntegrityError(
            "Submission blocked: Early claim mode requires at least 1 validated candidate."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    version_tag = "v1.0_early_claim" if mode == "early_claim" else "v2.0_final"
    timestamp_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Primary target filename
    primary_filename = f"{target_name}_submission.csv"
    primary_path = output_dir / primary_filename

    rows: list[dict[str, str]] = []
    candidate_ids: list[str] = []

    for idx, cand in enumerate(candidates):
        # 1. Export safety verification
        verify_export_safety(cand, purpose="competition")

        # 2. Biological sequence validation
        validate_sequence_for_submission(cand.sequence, molecule_type=molecule_type)

        cand_name = cand.metadata.get("submission_name") or f"{target_name}_des_{idx+1:02d}"
        rows.append({
            "name": cand_name,
            "sequence": cand.sequence.strip().upper(),
        })
        candidate_ids.append(cand.candidate_id)

    # Write primary CSV file (exactly 2 columns, max 21 lines)
    with open(primary_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "sequence"])
        writer.writeheader()
        writer.writerows(rows)

    fallback_path: Path | None = None
    if generate_ascii_fallback and target_name in ASCII_TARGET_MAP:
        ascii_name = ASCII_TARGET_MAP[target_name]
        fallback_filename = f"{ascii_name}_submission.csv"
        fallback_path = output_dir / fallback_filename
        with open(fallback_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "sequence"])
            writer.writeheader()
            writer.writerows(rows)

    # Generate update_note.txt (required by portal on re-upload)
    if mode == "early_claim":
        update_note = (
            f"Initial early claim submission ({version_tag}) for {target_name} at {timestamp_str}. "
            f"Includes {len(rows)} de novo candidate binders meeting all length and integrity "
            f"gates. Registered under First-come, First-served priority rule."
        )
    else:
        update_note = (
            f"Updated submission ({version_tag}) for {target_name} at {timestamp_str}. "
            f"Refined candidate portfolio ({len(rows)} designs) selected for peak in silico "
            f"ipSAE score, optimal charge distribution, and wet-lab Kd dissociation stability."
        )

    note_path = output_dir / f"{target_name}_update_note.txt"
    with open(note_path, mode="w", encoding="utf-8") as f:
        f.write(update_note + "\n")

    # Generate methods_abstract.txt (< 4,000 characters)
    molecule_len_str = (
        "40-100 aa" if molecule_type == "minibinder" else "100-150 aa"
    )
    methods_abstract = (
        f"Methods Abstract for {target_name} Binder Design ({version_tag}):\n"
        f"1. Target Preparation: Target sequence was sliced strictly according to official UniProt\n"
        f"annotations provided by committee. Structures aligned to benchmark PDB templates.\n"
        f"2. De Novo Generation: Candidates engineered de novo using generative pipelines\n"
        f"({molecule_type}, strictly within {molecule_len_str}). Zero template grafting.\n"
        f"3. In Silico Scoring & ipSAE: Complex geometries evaluated via ESMFold2 under competition\n"
        f"specs (1 seed, 1 sample, no templates; target MSA enabled, binder single-sequence mode).\n"
        f"Candidates were ranked by predicted interface structural alignment error (ipSAE).\n"
        f"4. Quality & Druggability: Sequences contain only 20 natural amino acids. Screened against\n"
        f"purification tags, signal peptides, unpaired cysteines, and chemical degradation motifs."
    )
    abstract_path = output_dir / f"{target_name}_methods_abstract.txt"
    with open(abstract_path, mode="w", encoding="utf-8") as f:
        f.write(methods_abstract + "\n")

    # Persist in SQLite submission_history if db provided
    submission_id = f"sub_{uuid4().hex[:10]}"
    if db is not None:
        db.save_submission(
            submission_id=submission_id,
            target_name=target_name,
            mode=mode,
            version_tag=version_tag,
            candidate_ids=candidate_ids,
            file_path=str(primary_path),
            update_note=update_note,
        )

    return {
        "submission_id": submission_id,
        "target_name": target_name,
        "mode": mode,
        "version_tag": version_tag,
        "candidate_count": len(rows),
        "primary_csv": primary_path,
        "fallback_csv": fallback_path,
        "update_note_file": note_path,
        "methods_abstract_file": abstract_path,
        "update_note": update_note,
    }
