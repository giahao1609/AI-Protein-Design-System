"""Unit tests for candidate lifecycle state machine."""

from __future__ import annotations

import pytest

from protein_design.schemas.common import CandidateStatus
from protein_design.core.lifecycle import validate_transition, is_terminal
from protein_design.core.exceptions import CandidateLifecycleError


class TestLifecycle:
    def test_valid_forward_transitions(self):
        """Test that the happy path works."""
        valid_path = [
            (CandidateStatus.CREATED, CandidateStatus.GENERATED),
            (CandidateStatus.GENERATED, CandidateStatus.SEQUENCE_VALIDATED),
            (CandidateStatus.SEQUENCE_VALIDATED, CandidateStatus.STRUCTURE_PREDICTED),
            (CandidateStatus.STRUCTURE_PREDICTED, CandidateStatus.STRUCTURE_CHECKED),
            (CandidateStatus.STRUCTURE_CHECKED, CandidateStatus.INTERFACE_CHECKED),
            (CandidateStatus.INTERFACE_CHECKED, CandidateStatus.DEVELOPABILITY_CHECKED),
            (CandidateStatus.DEVELOPABILITY_CHECKED, CandidateStatus.NOVELTY_CHECKED),
            (CandidateStatus.NOVELTY_CHECKED, CandidateStatus.VALID),
        ]
        for from_s, to_s in valid_path:
            validate_transition(from_s, to_s)  # Should not raise

    def test_rejection_from_any_check_stage(self):
        """Test that candidates can be rejected at various stages."""
        rejectable = [
            CandidateStatus.GENERATED,
            CandidateStatus.STRUCTURE_PREDICTED,
            CandidateStatus.STRUCTURE_CHECKED,
            CandidateStatus.INTERFACE_CHECKED,
            CandidateStatus.NOVELTY_CHECKED,
        ]
        for status in rejectable:
            validate_transition(status, CandidateStatus.REJECTED)

    def test_failure_from_any_stage(self):
        """Test that candidates can fail at any non-terminal stage."""
        for status in CandidateStatus:
            if not is_terminal(status):
                validate_transition(status, CandidateStatus.FAILED)

    def test_invalid_transition_raises(self):
        """Test that invalid transitions raise CandidateLifecycleError."""
        with pytest.raises(CandidateLifecycleError):
            validate_transition(
                CandidateStatus.CREATED,
                CandidateStatus.VALID,  # Can't skip to VALID
            )

    def test_terminal_states_have_no_transitions(self):
        terminal = [
            CandidateStatus.VALID,
            CandidateStatus.REJECTED,
            CandidateStatus.FAILED,
            CandidateStatus.INVALID,
            CandidateStatus.DUPLICATE,
        ]
        for status in terminal:
            assert is_terminal(status)

    def test_cannot_transition_from_terminal(self):
        with pytest.raises(CandidateLifecycleError):
            validate_transition(
                CandidateStatus.VALID,
                CandidateStatus.GENERATED,
            )
        with pytest.raises(CandidateLifecycleError):
            validate_transition(
                CandidateStatus.REJECTED,
                CandidateStatus.GENERATED,
            )

    def test_duplicate_detection_path(self):
        """Test the duplicate detection transition."""
        validate_transition(
            CandidateStatus.DEVELOPABILITY_CHECKED,
            CandidateStatus.DUPLICATE,
        )
