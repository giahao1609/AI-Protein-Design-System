"""Candidate schema — Represents a designed protein binder candidate."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from protein_design.schemas.common import (
    CandidateStatus,
    DesignType,
    DiversityInfo,
    NoveltyResult,
    ProvenanceRecord,
    QCResult,
    ScientificStatus,
    StatusTransition,
    generate_id,
    hash_string,
    utc_now,
)


class Candidate(BaseModel):
    """A designed protein binder candidate.

    Each candidate tracks its full lifecycle from generation through validation,
    including provenance, quality checks, and diversity information.

    Scientific status labels have strict definitions:
    - GENERATED: Model produced this. No validation performed.
    - COMPUTATIONALLY_VALIDATED: Passed independent computational checks.
    - EXPERIMENTALLY_TESTED: Wet-lab experiment performed.
    - EXPERIMENTALLY_VALIDATED: Wet-lab result supports binding claim.

    Candidates are NEVER deleted. Failed/rejected candidates are research data.
    """

    candidate_id: str = Field(default_factory=lambda: generate_id("cand"))
    target_id: str

    # Sequence
    sequence: str
    length: int = 0

    # Design info
    design_type: DesignType = DesignType.MINIBINDER
    generator: str = ""
    generator_version: str = ""
    seed: int | None = None

    # Lineage
    parent_candidate: str | None = Field(
        default=None, description="Parent candidate_id if this is a derivative design"
    )

    # Structure paths
    structure_path: Path | None = Field(
        default=None, description="Path to predicted binder structure"
    )
    complex_structure_path: Path | None = Field(
        default=None, description="Path to predicted binder-target complex structure"
    )

    # Metrics & QC (populated during pipeline stages)
    metrics: dict[str, Any] = Field(default_factory=dict)
    sequence_qc: QCResult | None = None
    structure_qc: QCResult | None = None
    interface_qc: QCResult | None = None
    developability: dict[str, Any] | None = None
    novelty: NoveltyResult | None = None

    # Diversity
    diversity_cluster: DiversityInfo | None = None

    # Metadata & Custom Attributes
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Status
    status: CandidateStatus = CandidateStatus.CREATED
    scientific_status: ScientificStatus = ScientificStatus.GENERATED
    status_history: list[StatusTransition] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=utc_now)

    # Provenance
    provenance: ProvenanceRecord | None = None

    # Computed hash
    sequence_hash: str = Field(default="")

    @model_validator(mode="after")
    def auto_populate(self) -> Candidate:
        """Auto-compute length and sequence_hash."""
        if self.length == 0:
            self.length = len(self.sequence)
        if not self.sequence_hash:
            self.sequence_hash = hash_string(self.sequence)
        return self

    def transition(
        self,
        new_status: CandidateStatus,
        reason: str,
        stage: str,
        metric_name: str | None = None,
        metric_value: float | None = None,
        threshold: float | None = None,
    ) -> None:
        """Transition candidate to a new status, recording the change.

        Every transition is recorded in status_history. This provides
        a complete audit trail of the candidate's lifecycle.
        """
        from protein_design.core.lifecycle import validate_transition
        validate_transition(self.status, new_status, self.candidate_id)

        transition = StatusTransition(
            from_status=self.status,
            to_status=new_status,
            reason=reason,
            stage=stage,
            metric_name=metric_name,
            metric_value=metric_value,
            threshold=threshold,
        )
        self.status_history.append(transition)
        self.status = new_status
