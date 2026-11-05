"""Export Safety Gate.

Enforces fail-closed export verification separating competition delivery
from scientific publication manuscripts, preventing dummy-validated candidates
from reaching external distribution.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from protein_design.core.exceptions import SecurityIntegrityError
from protein_design.schemas import Candidate


def verify_export_safety(
    candidate: Candidate,
    purpose: Literal["competition", "publication"] = "competition",
) -> bool:
    """Fail-closed export gate separating competition delivery from publication.

    Args:
        candidate: Candidate record to verify.
        purpose: Export target objective ('competition' or 'publication').

    Returns:
        True if the candidate passes all security and integrity checks.

    Raises:
        SecurityIntegrityError: If candidate fails validation checks or lacks required provenance.
    """
    if purpose not in ("competition", "publication"):
        raise SecurityIntegrityError(f"Export blocked: Unsupported purpose '{purpose}'")

    # Sequence integrity check
    upper_seq = candidate.sequence.strip().upper()
    if not upper_seq:
        raise SecurityIntegrityError("Export blocked: Candidate sequence is missing or empty.")

    # PROHIBITED TAGS & LABELS
    if "HHHHHH" in upper_seq:
        raise SecurityIntegrityError("Export blocked: Sequence contains His6-tag.")
    if "DYKDDDDK" in upper_seq:
        raise SecurityIntegrityError("Export blocked: Sequence contains Flag-tag.")
    if "EQKLISEEDL" in upper_seq:
        raise SecurityIntegrityError("Export blocked: Sequence contains Myc-tag.")
    if "WSHPQFEK" in upper_seq:
        raise SecurityIntegrityError("Export blocked: Sequence contains Strep-tag.")
    if upper_seq.startswith("GGGGS") or upper_seq.endswith("GGGGS"):
        raise SecurityIntegrityError(
            "Export blocked: Sequence contains redundant terminal GS linker."
        )

    # COMMON BLOCK 1: Dummy-only validation is unconditionally blocked for all exports
    if candidate.generator == "dummy":
        raise SecurityIntegrityError("Export blocked: Candidate produced by dummy generator.")

    validation_history = candidate.metadata.get("validation_history", [])
    if any("dummy" in str(v).lower() for v in validation_history):
        raise SecurityIntegrityError("Export blocked: Candidate passed only dummy validation.")

    # Check status history for dummy validation traces
    for transition in candidate.status_history:
        if "dummy" in transition.reason.lower() or "dummy" in transition.stage.lower():
            raise SecurityIntegrityError("Export blocked: Candidate passed only dummy validation.")

    # COMMON BLOCK 2: Missing or corrupted structure artifacts are unconditionally blocked
    struct_path = candidate.structure_path or candidate.complex_structure_path
    if not struct_path:
        raise SecurityIntegrityError(
            "Export blocked: Candidate structure coordinate file is missing."
        )

    if not Path(struct_path).exists():
        raise SecurityIntegrityError(
            f"Export blocked: Candidate structure file does not exist on disk: {struct_path}"
        )

    # PURPOSE-SPECIFIC GATING
    if purpose == "publication":
        # Publication gate strictly mandates 9-link provenance and publication_ready = True
        if not candidate.provenance:
            raise SecurityIntegrityError(
                "Export blocked for publication: Candidate lacks provenance record."
            )
        if not candidate.provenance.metadata.get("publication_ready", False):
            raise SecurityIntegrityError(
                "Export blocked for publication: Candidate not marked publication_ready "
                "with verified 9-link provenance."
            )

    elif purpose == "competition":
        # Competition gate validates competition submission eligibility and length constraints.
        # It does NOT mandate publication_ready = True.
        if len(candidate.sequence) < 20:
            raise SecurityIntegrityError(
                f"Export blocked for competition: Sequence length ({len(candidate.sequence)}) "
                "below minimum threshold of 20."
            )

    return True

