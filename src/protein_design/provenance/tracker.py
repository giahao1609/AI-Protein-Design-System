"""Provenance tracker — Captures full origin information for every artifact.

Every artifact must answer:
    - Who created it? (generator/model)
    - Which model version?
    - What was the input?
    - What config was used?
    - What random seed?
    - Which experiment run?
    - What code commit?
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

from protein_design.schemas.common import (
    HardwareInfo,
    ProvenanceRecord,
    hash_dict,
    hash_string,
    utc_now,
)
from protein_design.logging import get_logger

log = get_logger(module="provenance")


def get_git_commit() -> Optional[str]:
    """Get the current git commit hash, if in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def get_hardware_info() -> HardwareInfo:
    """Collect hardware information for reproducibility."""
    info = HardwareInfo(
        hostname=platform.node(),
        cpu=platform.processor() or platform.machine(),
        python_version=sys.version,
    )

    # Try to detect GPU
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,count", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            info.gpu = lines[0].split(",")[0].strip() if lines else None
            info.gpu_count = len(lines)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # CUDA version
    cuda_version = os.environ.get("CUDA_VERSION")
    if cuda_version:
        info.cuda_version = cuda_version

    return info


def create_provenance(
    run_id: str,
    target_id: str,
    generator: str,
    generator_version: str,
    config: dict[str, Any],
    random_seed: Optional[int] = None,
    model_checkpoint: Optional[str] = None,
    parent_candidate_id: Optional[str] = None,
    input_data: Optional[dict[str, str]] = None,
) -> ProvenanceRecord:
    """Create a full provenance record.

    Args:
        run_id: Experiment run ID.
        target_id: Target ID.
        generator: Generator name.
        generator_version: Generator version string.
        config: Full config dict (will be hashed).
        random_seed: Random seed used.
        model_checkpoint: Path/name of model checkpoint.
        parent_candidate_id: Parent candidate if derivative.
        input_data: Dict of input name → hash for input provenance.

    Returns:
        ProvenanceRecord with all fields populated.
    """
    hw = get_hardware_info()
    git_commit = get_git_commit()

    provenance = ProvenanceRecord(
        run_id=run_id,
        target_id=target_id,
        generator=generator,
        generator_version=generator_version,
        model_checkpoint=model_checkpoint,
        git_commit=git_commit,
        config_hash=hash_dict(config),
        random_seed=random_seed,
        hardware=f"{hw.cpu} | GPU: {hw.gpu or 'none'}",
        timestamp=utc_now(),
        input_hashes=input_data or {},
        parent_candidate_id=parent_candidate_id,
    )

    log.debug(
        "provenance_created",
        run_id=run_id,
        generator=generator,
        config_hash=provenance.config_hash,
        git_commit=git_commit,
    )

    return provenance
