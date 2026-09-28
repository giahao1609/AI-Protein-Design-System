"""Common types, enums, and shared schemas used across the system."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    uid = uuid4().hex[:12]
    if prefix:
        return f"{prefix}_{uid}"
    return uid


def generate_sequential_id(prefix: str, index: int) -> str:
    """Generate a zero-padded sequential ID."""
    return f"{prefix}_{index:06d}"


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def hash_string(value: str) -> str:
    """SHA-256 hash of a string."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_file(path: Path) -> str:
    """SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_dict(d: dict) -> str:
    """SHA-256 hash of a dict (via sorted JSON representation)."""
    import json
    serialized = json.dumps(d, sort_keys=True, default=str)
    return hash_string(serialized)


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------

def utc_now() -> datetime:
    """Current UTC datetime."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CandidateStatus(str, Enum):
    """Lifecycle status of a candidate in the pipeline."""
    CREATED = "CREATED"
    GENERATED = "GENERATED"
    SEQUENCE_VALIDATED = "SEQUENCE_VALIDATED"
    STRUCTURE_PREDICTED = "STRUCTURE_PREDICTED"
    STRUCTURE_CHECKED = "STRUCTURE_CHECKED"
    INTERFACE_CHECKED = "INTERFACE_CHECKED"
    DEVELOPABILITY_CHECKED = "DEVELOPABILITY_CHECKED"
    NOVELTY_CHECKED = "NOVELTY_CHECKED"
    VALID = "VALID"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    INVALID = "INVALID"
    DUPLICATE = "DUPLICATE"


class ScientificStatus(str, Enum):
    """Scientific validation level of a candidate.

    These labels have strict definitions:
    - GENERATED: Model produced this candidate. No validation.
    - COMPUTATIONALLY_VALIDATED: Passed independent computational checks.
    - EXPERIMENTALLY_TESTED: Wet-lab experiment performed, results pending or ambiguous.
    - EXPERIMENTALLY_VALIDATED: Wet-lab result supports the binding claim.
    """
    GENERATED = "GENERATED"
    COMPUTATIONALLY_VALIDATED = "COMPUTATIONALLY_VALIDATED"
    EXPERIMENTALLY_TESTED = "EXPERIMENTALLY_TESTED"
    EXPERIMENTALLY_VALIDATED = "EXPERIMENTALLY_VALIDATED"


class RunStatus(str, Enum):
    """Status of an experiment run."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PARTIAL = "PARTIAL"  # Some candidates succeeded, some failed


class EvidenceLevel(int, Enum):
    """Hierarchy of evidence reliability. Lower number = more reliable.

    AI reasoning is the LEAST reliable source.
    """
    EXPERIMENTAL_WETLAB = 1
    EXPERIMENTAL_DATABASE = 2
    PEER_REVIEWED = 3
    INDEPENDENT_COMPUTATIONAL = 4
    PREPRINT = 5
    MODEL_DOCUMENTATION = 6
    AI_REASONING = 7


class DesignType(str, Enum):
    """Type of designed protein."""
    MINIBINDER = "minibinder"
    VHH = "VHH"
    NANOBODY = "nanobody"
    PEPTIDE = "peptide"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Shared sub-models
# ---------------------------------------------------------------------------

class ChainInfo(BaseModel):
    """Information about a protein chain."""
    chain_id: str
    sequence: str
    length: int
    description: Optional[str] = None


class DomainInfo(BaseModel):
    """Known domain in a protein."""
    name: str
    start: int
    end: int
    source: Optional[str] = None  # e.g., Pfam ID


class InterfaceInfo(BaseModel):
    """Known interface region."""
    name: str
    residues: list[int]
    partner: Optional[str] = None
    source: Optional[str] = None


class HotspotInfo(BaseModel):
    """Binding hotspot residue."""
    residue: int
    chain_id: str
    importance: Optional[float] = None
    source: Optional[str] = None


class EpitopeInfo(BaseModel):
    """Known epitope region."""
    name: str
    residues: list[int]
    chain_id: str
    antibody_type: Optional[str] = None
    source: Optional[str] = None


class QCResult(BaseModel):
    """Quality control result for a check."""
    passed: bool
    metric_name: str
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


class NoveltyResult(BaseModel):
    """Result of novelty checking."""
    is_novel: bool
    closest_match: Optional[str] = None
    similarity_score: Optional[float] = None
    search_database: Optional[str] = None
    details: dict[str, Any] = Field(default_factory=dict)


class DiversityInfo(BaseModel):
    """Diversity clustering information for a candidate."""
    sequence_cluster: Optional[str] = None
    structure_cluster: Optional[str] = None
    interface_cluster: Optional[str] = None
    binding_mode_cluster: Optional[str] = None
    generator_family: Optional[str] = None


class StatusTransition(BaseModel):
    """Record of a candidate status change."""
    from_status: CandidateStatus
    to_status: CandidateStatus
    reason: str
    stage: str
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    timestamp: datetime = Field(default_factory=utc_now)


class ProvenanceRecord(BaseModel):
    """Full provenance for an artifact."""
    run_id: str
    target_id: str
    generator: str
    generator_version: str
    model_checkpoint: Optional[str] = None
    git_commit: Optional[str] = None
    config_hash: str
    random_seed: Optional[int] = None
    hardware: Optional[str] = None
    timestamp: datetime = Field(default_factory=utc_now)
    input_hashes: dict[str, str] = Field(default_factory=dict)
    parent_candidate_id: Optional[str] = None


class HardwareInfo(BaseModel):
    """Hardware information for reproducibility."""
    hostname: Optional[str] = None
    cpu: Optional[str] = None
    gpu: Optional[str] = None
    gpu_count: int = 0
    ram_gb: Optional[float] = None
    cuda_version: Optional[str] = None
    python_version: Optional[str] = None


class ErrorRecord(BaseModel):
    """Record of an error during pipeline execution."""
    candidate_id: Optional[str] = None
    stage: str
    error_type: str
    error_message: str
    traceback: Optional[str] = None
    timestamp: datetime = Field(default_factory=utc_now)
    recoverable: bool = True
