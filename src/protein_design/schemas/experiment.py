"""ExperimentRun schema — Represents a single pipeline execution."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from protein_design.schemas.common import (
    ErrorRecord,
    HardwareInfo,
    RunStatus,
    generate_id,
    utc_now,
)


class ExperimentRun(BaseModel):
    """A single execution of the design pipeline.

    Captures everything needed for reproducibility:
    - Exact config used (via config_hash)
    - Code version (via git_commit)
    - Environment and hardware
    - Random seed
    - All candidates produced
    - Errors encountered

    Runs with status PARTIAL indicate some candidates succeeded while
    others failed. The errors list provides details on failures.
    """

    run_id: str = Field(default_factory=lambda: generate_id("run"))
    target_id: str
    pipeline_version: str = ""
    config_hash: str = ""
    git_commit: Optional[str] = None

    # Environment
    environment: dict[str, str] = Field(
        default_factory=dict,
        description="Key environment variables and package versions",
    )
    hardware: HardwareInfo = Field(default_factory=HardwareInfo)

    # Timing
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: Optional[datetime] = None

    # Reproducibility
    random_seed: int = 42

    # I/O
    input_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Full configuration used for this run",
    )
    output_summary: Optional[dict[str, Any]] = None
    candidate_ids: list[str] = Field(default_factory=list)

    # Status
    status: RunStatus = RunStatus.PENDING
    errors: list[ErrorRecord] = Field(default_factory=list)

    # Checkpoint
    checkpoint_path: Optional[Path] = Field(
        default=None,
        description="Path to checkpoint file for resume capability",
    )

    def mark_started(self) -> None:
        """Mark the run as started."""
        self.status = RunStatus.RUNNING
        self.started_at = utc_now()

    def mark_completed(self, summary: Optional[dict] = None) -> None:
        """Mark the run as completed."""
        self.status = RunStatus.COMPLETED
        self.finished_at = utc_now()
        if summary:
            self.output_summary = summary

    def mark_failed(self, error: ErrorRecord) -> None:
        """Mark the run as failed."""
        self.status = RunStatus.FAILED
        self.finished_at = utc_now()
        self.errors.append(error)

    def mark_partial(self) -> None:
        """Mark the run as partially completed (some candidates failed)."""
        self.status = RunStatus.PARTIAL
        self.finished_at = utc_now()

    def add_error(self, error: ErrorRecord) -> None:
        """Record an error without changing run status."""
        self.errors.append(error)

    def add_candidate(self, candidate_id: str) -> None:
        """Register a candidate produced by this run."""
        self.candidate_ids.append(candidate_id)
