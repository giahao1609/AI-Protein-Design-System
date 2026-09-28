"""Config loader — Load, merge, and validate YAML configurations.

Design principle: NO scientific thresholds hardcoded in Python.
All thresholds come from config files and must be:
    benchmark → calibrate → config

Wrong:
    if iptm > 0.8:  # hardcoded

Right:
    threshold = config.validation.iptm.threshold
    if threshold is not None and iptm > threshold:
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field

from protein_design.schemas.common import hash_dict


# ---------------------------------------------------------------------------
# Config schema models
# ---------------------------------------------------------------------------

class MetricConfig(BaseModel):
    """Configuration for a single validation metric.

    threshold=None means the metric has not been calibrated yet.
    It will be computed but NOT used for filtering until a threshold
    is established through benchmarking.
    """
    enabled: bool = True
    threshold: Optional[float] = None
    direction: str = Field(
        default="higher_better",
        description="'higher_better' or 'lower_better'",
    )
    weight: Optional[float] = None


class ValidationConfig(BaseModel):
    """Configuration for all validation metrics."""
    plddt: MetricConfig = Field(default_factory=MetricConfig)
    ptm: MetricConfig = Field(default_factory=MetricConfig)
    iptm: MetricConfig = Field(default_factory=MetricConfig)
    pae: MetricConfig = Field(default_factory=lambda: MetricConfig(direction="lower_better"))
    clash_score: MetricConfig = Field(
        default_factory=lambda: MetricConfig(direction="lower_better")
    )
    interface_contacts: MetricConfig = Field(default_factory=MetricConfig)
    sasa: MetricConfig = Field(default_factory=MetricConfig)
    custom: dict[str, MetricConfig] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)


class GenerationConfig(BaseModel):
    """Configuration for candidate generation."""
    generator: str = "dummy"
    num_candidates: int = 10
    random_seed: int = 42
    design_type: str = "minibinder"
    params: dict[str, Any] = Field(default_factory=dict)


class PredictionConfig(BaseModel):
    """Configuration for structure prediction."""
    predictor: str = "dummy"
    params: dict[str, Any] = Field(default_factory=dict)


class StorageConfig(BaseModel):
    """Configuration for storage paths."""
    database_path: str = "protein_design.db"
    candidates_dir: str = "candidates"
    experiments_dir: str = "experiments"
    evidence_dir: str = "evidence"
    audit_dir: str = "audit"


class PipelineConfig(BaseModel):
    """Top-level pipeline configuration.

    This aggregates all sub-configs. No scientific parameters
    should appear outside of these config structures.
    """
    project_name: str = "protein-design"
    version: str = "0.1.0"
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    prediction: PredictionConfig = Field(default_factory=PredictionConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    custom: dict[str, Any] = Field(default_factory=dict)

    @property
    def config_hash(self) -> str:
        """Compute hash of this configuration for provenance."""
        return hash_dict(self.model_dump())


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_yaml(path: Path) -> dict[str, Any]:
    """Load a single YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if data is not None else {}


def merge_configs(*configs: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge multiple config dicts. Later configs override earlier ones."""
    result: dict[str, Any] = {}
    for config in configs:
        _deep_merge(result, config)
    return result


def _deep_merge(base: dict, override: dict) -> None:
    """Recursively merge override into base."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def load_config(
    base_path: Optional[Path] = None,
    override_paths: Optional[list[Path]] = None,
    overrides: Optional[dict[str, Any]] = None,
) -> PipelineConfig:
    """Load and validate pipeline configuration.

    Args:
        base_path: Path to base YAML config file.
        override_paths: Additional YAML files to merge (overrides base).
        overrides: Dict of final overrides (e.g., from CLI).

    Returns:
        Validated PipelineConfig.
    """
    config_data: dict[str, Any] = {}

    # Load base config
    if base_path and base_path.exists():
        config_data = load_yaml(base_path)

    # Merge override files
    if override_paths:
        for path in override_paths:
            if path.exists():
                override_data = load_yaml(path)
                _deep_merge(config_data, override_data)

    # Apply programmatic overrides
    if overrides:
        _deep_merge(config_data, overrides)

    # Environment variable overrides
    env_log_level = os.environ.get("PROTEIN_DESIGN_LOG_LEVEL")
    if env_log_level:
        config_data.setdefault("custom", {})["log_level"] = env_log_level

    return PipelineConfig(**config_data)


def save_config(config: PipelineConfig, path: Path) -> None:
    """Save a PipelineConfig to YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            config.model_dump(),
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
