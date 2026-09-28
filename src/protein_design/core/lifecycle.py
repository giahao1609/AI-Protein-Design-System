"""Candidate lifecycle state machine.

Defines valid state transitions and enforces them.
Every transition is recorded — invalid transitions raise CandidateLifecycleError.
"""

from __future__ import annotations

from protein_design.schemas.common import CandidateStatus
from protein_design.core.exceptions import CandidateLifecycleError


# Valid transitions: from_status → set of allowed to_statuses
VALID_TRANSITIONS: dict[CandidateStatus, set[CandidateStatus]] = {
    CandidateStatus.CREATED: {
        CandidateStatus.GENERATED,
        CandidateStatus.INVALID,
        CandidateStatus.FAILED,
    },
    CandidateStatus.GENERATED: {
        CandidateStatus.SEQUENCE_VALIDATED,
        CandidateStatus.REJECTED,
        CandidateStatus.INVALID,
        CandidateStatus.DUPLICATE,
        CandidateStatus.FAILED,
    },
    CandidateStatus.SEQUENCE_VALIDATED: {
        CandidateStatus.STRUCTURE_PREDICTED,
        CandidateStatus.REJECTED,
        CandidateStatus.INVALID,
        CandidateStatus.FAILED,
    },
    CandidateStatus.STRUCTURE_PREDICTED: {
        CandidateStatus.STRUCTURE_CHECKED,
        CandidateStatus.REJECTED,
        CandidateStatus.INVALID,
        CandidateStatus.FAILED,
    },
    CandidateStatus.STRUCTURE_CHECKED: {
        CandidateStatus.INTERFACE_CHECKED,
        CandidateStatus.REJECTED,
        CandidateStatus.INVALID,
        CandidateStatus.FAILED,
    },
    CandidateStatus.INTERFACE_CHECKED: {
        CandidateStatus.DEVELOPABILITY_CHECKED,
        CandidateStatus.REJECTED,
        CandidateStatus.INVALID,
        CandidateStatus.FAILED,
    },
    CandidateStatus.DEVELOPABILITY_CHECKED: {
        CandidateStatus.NOVELTY_CHECKED,
        CandidateStatus.DUPLICATE,
        CandidateStatus.REJECTED,
        CandidateStatus.INVALID,
        CandidateStatus.FAILED,
    },
    CandidateStatus.NOVELTY_CHECKED: {
        CandidateStatus.VALID,
        CandidateStatus.REJECTED,
        CandidateStatus.INVALID,
        CandidateStatus.DUPLICATE,
        CandidateStatus.FAILED,
    },
    # Terminal states — no further transitions
    CandidateStatus.VALID: set(),
    CandidateStatus.REJECTED: set(),
    CandidateStatus.FAILED: set(),
    CandidateStatus.INVALID: set(),
    CandidateStatus.DUPLICATE: set(),
}


def validate_transition(
    from_status: CandidateStatus,
    to_status: CandidateStatus,
    candidate_id: str = "",
) -> None:
    """Validate that a status transition is allowed.

    Raises:
        CandidateLifecycleError: If the transition is not valid.
    """
    allowed = VALID_TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise CandidateLifecycleError(
            candidate_id=candidate_id,
            from_status=from_status.value,
            to_status=to_status.value,
        )


def is_terminal(status: CandidateStatus) -> bool:
    """Check if a status is terminal (no further transitions allowed)."""
    return len(VALID_TRANSITIONS.get(status, set())) == 0
