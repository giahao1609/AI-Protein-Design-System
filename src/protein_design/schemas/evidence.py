"""EvidenceRecord schema — Tracks scientific evidence for claims."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from protein_design.schemas.common import (
    EvidenceLevel,
    generate_id,
    utc_now,
)


class EvidenceRecord(BaseModel):
    """A single piece of scientific evidence supporting or refuting a claim.

    Evidence is ranked by reliability level (EvidenceLevel):
    1. Experimental wet-lab evidence (most reliable)
    2. Experimental databases (PDB, curated datasets)
    3. Peer-reviewed papers
    4. Independent computational evidence
    5. Preprints
    6. Model documentation / GitHub
    7. AI reasoning (least reliable)

    AI prediction is NEVER treated as ground truth.
    """

    evidence_id: str = Field(default_factory=lambda: generate_id("evi"))
    claim: str = Field(description="The scientific claim this evidence relates to")
    source_type: str = Field(
        description="Type of source (e.g., 'paper', 'database', 'wet-lab', 'computational')"
    )
    source: str = Field(description="Human-readable source description")

    # Identifiers
    doi: Optional[str] = None
    pdb_id: Optional[str] = None
    uniprot_id: Optional[str] = None
    url: Optional[str] = None

    # Metadata
    date_accessed: datetime = Field(default_factory=utc_now)
    evidence_level: EvidenceLevel
    notes: str = ""
