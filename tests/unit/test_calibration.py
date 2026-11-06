"""Unit tests for calibration schema validation, SNR assessment, and offline fixtures."""

from __future__ import annotations

import pytest

from pydantic import ValidationError as PydanticValidationError

from protein_design.core.exceptions import ValidationError
from protein_design.validation.calibration import (
    CalibrationReport,
    DecoyDistributionSchema,
    TargetThresholdPayload,
    assess_calibration_quality,
    update_target_calibration,
    validate_thresholds_payload,
)

# Explicitly labeled synthetic fixture for testing only
SYNTHETIC_FIXTURE_DO_NOT_USE_IN_PROD = {
    "generated_at": "2026-11-06T00:00:00Z",
    "execution_id": "execution_24000_calibration_mock",
    "tracks": {
        "EGFR": {
            "target_id": "EGFR",
            "track_id": 1,
            "baseline_true_ipsae": 0.824,
            "decoy_distribution": {
                "mean": 0.221,
                "std": 0.045,
                "p95": 0.285,
                "num_decoys": 20,
            },
            "noise_floor_ipsae": 0.285,
            "calibrated_threshold": 0.554,
            "calibration_status": "CALIBRATED",
            "method": "mean_plus_2std",
        },
        "TL1A": {
            "target_id": "TL1A",
            "track_id": 5,
            "baseline_true_ipsae": 0.742,
            "decoy_distribution": {
                "mean": 0.250,
                "std": 0.060,
                "p95": 0.340,
                "num_decoys": 20,
            },
            "noise_floor_ipsae": 0.340,
            "calibrated_threshold": 0.541,
            "calibration_status": "CALIBRATED",
            "method": "mean_plus_2std",
        },
    },
}


def test_validate_thresholds_payload_valid_fixture():
    report = validate_thresholds_payload(SYNTHETIC_FIXTURE_DO_NOT_USE_IN_PROD)
    assert isinstance(report, CalibrationReport)
    assert len(report.tracks) == 2
    assert "EGFR" in report.tracks
    assert report.tracks["EGFR"].baseline_true_ipsae == 0.824


def test_validate_thresholds_payload_rejects_malformed_json():
    corrupted = {"generated_at": "today"}  # Missing tracks
    with pytest.raises(ValidationError, match="Invalid thresholds.json schema"):
        validate_thresholds_payload(corrupted)


def test_assess_calibration_quality_high_confidence():
    payload = TargetThresholdPayload(
        target_id="EGFR",
        track_id=1,
        baseline_true_ipsae=0.824,
        decoy_distribution=DecoyDistributionSchema(mean=0.22, std=0.04, p95=0.28, num_decoys=20),
        noise_floor_ipsae=0.28,
        calibrated_threshold=0.55,
    )
    quality = assess_calibration_quality(payload)
    assert quality["is_reliable"] is True
    assert quality["snr"] > 2.0
    assert quality["separation_margin"] > 0.5


def test_assess_calibration_quality_poor_snr():
    payload = TargetThresholdPayload(
        target_id="POOR_TARGET",
        track_id=2,
        baseline_true_ipsae=0.32,
        decoy_distribution=DecoyDistributionSchema(mean=0.29, std=0.05, p95=0.31, num_decoys=20),
        noise_floor_ipsae=0.31,
        calibrated_threshold=0.315,
    )
    quality = assess_calibration_quality(payload)
    assert quality["is_reliable"] is False
    assert quality["snr"] < 1.1


def test_update_target_calibration_applies_metrics():
    payload = TargetThresholdPayload(
        target_id="EGFR",
        track_id=1,
        baseline_true_ipsae=0.824,
        decoy_distribution=DecoyDistributionSchema(mean=0.22, std=0.04, p95=0.28, num_decoys=20),
        noise_floor_ipsae=0.28,
        calibrated_threshold=0.55,
    )
    initial_meta = {"track_id": 1, "molecule_type": "VHH"}
    updated = update_target_calibration(initial_meta, payload)

    assert updated["baseline_true_ipsae"] == 0.824
    assert updated["noise_floor_ipsae"] == 0.28
    assert updated["calibrated_threshold"] == 0.55
    assert updated["calibration_status"] == "CALIBRATED_EMPIRICAL"
    assert "calibration_snr" in updated


def test_assess_calibration_quality_near_zero_denominator():
    payload = TargetThresholdPayload(
        target_id="TINY_NOISE",
        track_id=3,
        baseline_true_ipsae=0.75,
        decoy_distribution=DecoyDistributionSchema(mean=0.0, std=0.0, p95=0.0, num_decoys=20),
        noise_floor_ipsae=0.0,
        calibrated_threshold=0.50,
    )
    quality = assess_calibration_quality(payload)
    assert quality["is_reliable"] is False
    assert any("Near-zero" in w for w in quality["warnings"])


def test_assess_calibration_quality_insufficient_decoys():
    payload = TargetThresholdPayload(
        target_id="FEW_DECOYS",
        track_id=4,
        baseline_true_ipsae=0.80,
        decoy_distribution=DecoyDistributionSchema(mean=0.20, std=0.05, p95=0.25, num_decoys=5),
        noise_floor_ipsae=0.25,
        calibrated_threshold=0.50,
    )
    quality = assess_calibration_quality(payload)
    assert quality["is_reliable"] is False
    assert any("Insufficient decoy" in w for w in quality["warnings"])


def test_calibration_schema_rejects_nan():
    with pytest.raises(PydanticValidationError):
        TargetThresholdPayload(
            target_id="NAN_TARGET",
            track_id=1,
            baseline_true_ipsae=float("nan"),
            decoy_distribution=DecoyDistributionSchema(mean=0.2, std=0.05, p95=0.25, num_decoys=20),
            noise_floor_ipsae=0.25,
            calibrated_threshold=0.50,
        )


def test_update_target_calibration_rejects_synthetic_fixture_in_production():
    payload = TargetThresholdPayload(
        target_id="EGFR",
        track_id=1,
        baseline_true_ipsae=0.80,
        decoy_distribution=DecoyDistributionSchema(mean=0.20, std=0.05, p95=0.25, num_decoys=20),
        noise_floor_ipsae=0.25,
        calibrated_threshold=0.50,
        calibration_status="SYNTHETIC_TEST_FIXTURE",
    )
    initial_meta = {"track_id": 1}
    with pytest.raises(ValidationError, match="rejected synthetic calibration fixture"):
        update_target_calibration(initial_meta, payload, enforce_production=True)
