"""Target schema — Represents the protein target to design binders for."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator

from protein_design.schemas.common import (
    ChainInfo,
    DomainInfo,
    EpitopeInfo,
    HotspotInfo,
    InterfaceInfo,
    generate_id,
    hash_string,
    utc_now,
)


class Target(BaseModel):
    """A protein target that binders will be designed against.

    The target contains all known structural and functional information
    needed by generators and validators. Source references must be provided
    for any scientific claims about the target.
    """

    target_id: str = Field(default_factory=lambda: generate_id("tgt"))
    name: str
    source: str = Field(
        description="Origin of target info (e.g., 'PDB', 'competition', 'literature')"
    )
    sequence: str = Field(description="Full amino acid sequence")
    structure_file: Optional[Path] = Field(
        default=None, description="Path to structure file (PDB/CIF)"
    )
    structure_source: Optional[str] = Field(
        default=None, description="Source of structure (e.g., 'PDB:7XYZ', 'AlphaFold')"
    )

    # Chain information
    chains: list[ChainInfo] = Field(default_factory=list)
    residue_numbering: Optional[str] = Field(
        default=None, description="Numbering scheme (e.g., 'author', 'PDB', 'UniProt')"
    )

    # Known annotations
    known_domains: list[DomainInfo] = Field(default_factory=list)
    known_interfaces: list[InterfaceInfo] = Field(default_factory=list)
    known_ligands: list[str] = Field(default_factory=list)
    known_glycosylation: list[int] = Field(
        default_factory=list, description="Glycosylation site residue positions"
    )
    hotspots: list[HotspotInfo] = Field(default_factory=list)
    epitopes: list[EpitopeInfo] = Field(default_factory=list)

    # Metadata
    notes: str = ""
    source_references: list[str] = Field(
        default_factory=list,
        description="DOIs, PDB IDs, URLs — evidence sources for target information",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

    # Computed
    target_hash: str = Field(
        default="",
        description="SHA-256 hash of sequence (+ structure file if available)",
    )

    @model_validator(mode="after")
    def compute_hash(self) -> "Target":
        """Compute target_hash from sequence and structure if not already set."""
        if not self.target_hash:
            hash_input = self.sequence
            if self.structure_file and self.structure_file.exists():
                from protein_design.schemas.common import hash_file
                hash_input += hash_file(self.structure_file)
            self.target_hash = hash_string(hash_input)
        return self

    @property
    def sequence_length(self) -> int:
        """Length of the target sequence."""
        return len(self.sequence)
