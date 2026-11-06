"""Common types, enums, and shared schemas used across the system."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any
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
    return datetime.now(UTC)


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


class ScoreProvenance(str, Enum):
    """Scientific score provenance classification.

    Prevents simulated, proxy, or synthetic numbers from masquerading as real predictions.
    """
    HEURISTIC_PROXY = "HEURISTIC_PROXY"
    MODEL_PREDICTED = "MODEL_PREDICTED"
    EXPERIMENTAL = "EXPERIMENTAL"
    UNVERIFIED = "UNVERIFIED"


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
    description: str | None = None


class DomainInfo(BaseModel):
    """Known domain in a protein."""
    name: str
    start: int
    end: int
    source: str | None = None  # e.g., Pfam ID


class InterfaceInfo(BaseModel):
    """Known interface region."""
    name: str
    residues: list[int]
    partner: str | None = None
    source: str | None = None


class HotspotInfo(BaseModel):
    """Binding hotspot residue."""
    residue: int
    chain_id: str
    importance: float | None = None
    source: str | None = None


class EpitopeInfo(BaseModel):
    """Known epitope region."""
    name: str
    residues: list[int]
    chain_id: str
    antibody_type: str | None = None
    source: str | None = None


class QCResult(BaseModel):
    """Quality control result for a check."""
    passed: bool
    metric_name: str
    metric_value: float | None = None
    threshold: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


class NoveltyResult(BaseModel):
    """Result of novelty checking."""
    is_novel: bool
    closest_match: str | None = None
    similarity_score: float | None = None
    search_database: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class DiversityInfo(BaseModel):
    """Diversity clustering information for a candidate."""
    sequence_cluster: str | None = None
    structure_cluster: str | None = None
    interface_cluster: str | None = None
    binding_mode_cluster: str | None = None
    generator_family: str | None = None


class StatusTransition(BaseModel):
    """Record of a candidate status change."""
    from_status: CandidateStatus
    to_status: CandidateStatus
    reason: str
    stage: str
    metric_name: str | None = None
    metric_value: float | None = None
    threshold: float | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class ProvenanceRecord(BaseModel):
    """Full provenance for an artifact."""
    run_id: str
    target_id: str
    generator: str
    generator_version: str
    model_checkpoint: str | None = None
    git_commit: str | None = None
    config_hash: str
    random_seed: int | None = None
    hardware: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)
    input_hashes: dict[str, str] = Field(default_factory=dict)
    parent_candidate_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HardwareInfo(BaseModel):
    """Hardware information for reproducibility."""
    hostname: str | None = None
    cpu: str | None = None
    gpu: str | None = None
    gpu_count: int = 0
    ram_gb: float | None = None
    cuda_version: str | None = None
    python_version: str | None = None


class ErrorRecord(BaseModel):
    """Record of an error during pipeline execution."""
    candidate_id: str | None = None
    stage: str
    error_type: str
    error_message: str
    traceback: str | None = None
    timestamp: datetime = Field(default_factory=utc_now)
    recoverable: bool = True
