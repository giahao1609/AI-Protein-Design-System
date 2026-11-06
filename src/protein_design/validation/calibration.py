"""Calibration Thresholds Ingestion and Validation Engine.

Parses and validates the official thresholds.json payload produced by AsterFire threshold_compute,
computes signal-to-noise ratio (SNR) against decoy distributions, and prepares verified thresholds
for target configuration without silent proxy substitution or fabrication.
"""

from __future__ import annotations

from __future__ import annotations

import math
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field, field_validator

from protein_design.core.exceptions import ValidationError

log = structlog.get_logger(__name__)


class CalibrationStatus(str, Enum):
    """Provenance state of calibration data."""

    CALIBRATED_EMPIRICAL = "CALIBRATED_EMPIRICAL"
    SYNTHETIC_TEST_FIXTURE = "SYNTHETIC_TEST_FIXTURE"
    UNCALIBRATED = "UNCALIBRATED"


class DecoyDistributionSchema(BaseModel):
    """Statistical summary of the negative control decoy complexes for a track."""

    mean: float = Field(..., ge=0.0, le=1.0)
    std: float = Field(..., ge=0.0, le=0.5)
    p95: float = Field(..., ge=0.0, le=1.0)
    num_decoys: int = Field(..., ge=1, le=500)

    @field_validator("mean", "std", "p95")
    @classmethod
    def validate_finite_decoy_stats(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError(f"Decoy distribution statistics must be finite numbers, got {v}")
        return v


class TargetThresholdPayload(BaseModel):
    """Schema for individual target calibration results in thresholds.json."""

    target_id: str
    track_id: int = Field(..., ge=1, le=7)
    baseline_true_ipsae: float = Field(..., ge=0.0, le=1.0)
    decoy_distribution: DecoyDistributionSchema
    noise_floor_ipsae: float = Field(..., ge=0.0, le=1.0)
    calibrated_threshold: float = Field(..., ge=0.0, le=1.0)
    calibration_status: str = Field(default=CalibrationStatus.CALIBRATED_EMPIRICAL.value)
    method: str = Field(default="mean_plus_2std")

    @field_validator("baseline_true_ipsae", "noise_floor_ipsae", "calibrated_threshold")
    @classmethod
    def validate_finite_scores(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError(f"Calibration score must be finite, got {v}")
        return v

    @field_validator("calibrated_threshold")
    @classmethod
    def validate_threshold_separation(cls, v: float, info: Any) -> float:
        """Verify that calibrated threshold is strictly above zero."""
        if v <= 0.05:
            raise ValueError(f"Calibrated threshold {v} is too low for meaningful discrimination")
        return v


class CalibrationReport(BaseModel):
    """Full container for multi-track thresholds.json."""

    generated_at: str
    execution_id: str
    tracks: dict[str, TargetThresholdPayload]


def validate_thresholds_payload(raw_json: dict[str, Any]) -> CalibrationReport:
    """Validate raw JSON dictionary from thresholds.json against Pydantic schema."""
    try:
        report = CalibrationReport.model_validate(raw_json)
        log.info("thresholds_json_validated", total_tracks=len(report.tracks))
        return report
    except Exception as exc:
        raise ValidationError(f"Invalid thresholds.json schema: {exc}") from exc


def assess_calibration_quality(payload: TargetThresholdPayload) -> dict[str, Any]:
    """Calculate Signal-to-Noise Ratio (SNR) and dynamic range between true complex and decoys.

    Guards against zero/near-zero denominators, non-finite values, and insufficient decoy samples.
    Acceptable discrimination requires SNR >= 1.25, separation_margin >= 0.10, and num_decoys >= 20.
    """
    baseline = payload.baseline_true_ipsae
    noise = payload.noise_floor_ipsae
    num_decoys = payload.decoy_distribution.num_decoys

    warnings: list[str] = []

    # Non-finite guard
    if not (math.isfinite(baseline) and math.isfinite(noise)):
        return {
            "target_id": payload.target_id,
            "track_id": payload.track_id,
            "snr": None,
            "separation_margin": None,
            "is_reliable": False,
            "warnings": ["Non-finite score encountered in calibration payload"],
            "recommended_threshold": payload.calibrated_threshold,
        }

    # Zero or near-zero denominator guard (< 1e-4)
    if noise < 1e-4:
        warnings.append("Near-zero decoy noise floor (< 1e-4); division by zero prevented")
        snr = 0.0
    else:
        snr = baseline / noise

    # Non-positive baseline check
    if baseline <= 0.0:
        warnings.append("Non-positive baseline true ipSAE")

    # Insufficient decoy count check (< 20)
    if num_decoys < 20:
        warnings.append(f"Insufficient decoy observations ({num_decoys} < 20 required for statistical significance)")

    separation_margin = baseline - noise
    is_reliable = (snr >= 1.25) and (separation_margin >= 0.10) and (num_decoys >= 20) and not warnings

    return {
        "target_id": payload.target_id,
        "track_id": payload.track_id,
        "snr": round(float(snr), 3) if snr is not None else None,
        "separation_margin": round(float(separation_margin), 4),
        "is_reliable": is_reliable,
        "warnings": warnings,
        "recommended_threshold": payload.calibrated_threshold,
    }


def update_target_calibration(
    target_metadata: dict[str, Any],
    calibration: TargetThresholdPayload,
    enforce_quality: bool = True,
    enforce_production: bool = False,
) -> dict[str, Any]:
    """Safely apply verified calibration metrics into target configuration metadata.

    Rejects unverified or fabricated inputs and prevents synthetic fixtures from entering production.
    """
    if enforce_production and calibration.calibration_status == CalibrationStatus.SYNTHETIC_TEST_FIXTURE.value:
        raise ValidationError(
            f"Target '{calibration.target_id}' rejected synthetic calibration fixture in production mode"
        )

    quality = assess_calibration_quality(calibration)
    if enforce_quality and not quality["is_reliable"]:
        log.warning(
            "unreliable_calibration_warning",
            target_id=calibration.target_id,
            snr=quality["snr"],
            separation_margin=quality["separation_margin"],
            warnings=quality["warnings"],
        )

    updated = dict(target_metadata)
    updated["baseline_true_ipsae"] = calibration.baseline_true_ipsae
    updated["noise_floor_ipsae"] = calibration.noise_floor_ipsae
    updated["calibrated_threshold"] = calibration.calibrated_threshold
    updated["calibration_status"] = calibration.calibration_status
    updated["calibration_snr"] = quality["snr"]
    updated["calibration_reliable"] = quality["is_reliable"]
    return updated
