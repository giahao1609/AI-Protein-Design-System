"""DecisionRecord schema — Tracks scientific decisions with evidence."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from protein_design.schemas.common import (
    generate_id,
    utc_now,
)


class DecisionRecord(BaseModel):
    """A scientific decision with supporting and counter evidence.

    Follows the chain:
        CLAIM → EVIDENCE → INDEPENDENT CHECK → BENCHMARK → DECISION

    Decisions are versioned: if a decision is revised, the new record
    links to the old one via `supersedes`. Old decisions are NEVER deleted.

    Confidence is expressed as a float 0.0–1.0 and must be justified
    by the evidence, not by AI assertion.
    """

    decision_id: str = Field(default_factory=lambda: generate_id("dec"))
    question: str = Field(description="The question being decided")
    claim: str = Field(description="The claim or hypothesis")

    # Evidence
    supporting_evidence: list[str] = Field(
        default_factory=list,
        description="List of evidence_ids supporting the claim",
    )
    counter_evidence: list[str] = Field(
        default_factory=list,
        description="List of evidence_ids against the claim",
    )
    benchmark_result: Optional[str] = Field(
        default=None,
        description="Reference to benchmark that tested this claim",
    )

    # Decision
    decision: str = Field(description="The decision made")
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence level (0.0–1.0), must be evidence-backed",
    )

    # Metadata
    date: datetime = Field(default_factory=utc_now)
    author: str = Field(description="Who made this decision (person or system)")
    supersedes: Optional[str] = Field(
        default=None,
        description="decision_id of the previous decision this replaces",
    )
