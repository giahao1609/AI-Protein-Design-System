"""Dummy Validator — Applies configurable pass/fail rules for testing.

All thresholds come from config. If a threshold is None, the check
always passes (metric computed but not filtered).
"""

from __future__ import annotations

from typing import Any, Optional

from protein_design.validation.base import BaseValidator, ValidationResult
from protein_design.schemas import Candidate, QCResult


class DummyValidator(BaseValidator):
    """Validates candidates using configurable thresholds from config."""

    @property
    def name(self) -> str:
        return "dummy"

    def validate(
        self,
        candidate: Candidate,
        config: dict[str, Any],
    ) -> ValidationResult:
        """Run dummy validation checks based on candidate metrics and config thresholds.

        For each metric in config, if threshold is not None,
        compare metric value against threshold.
        """
        params = config.get("params", {}) if isinstance(config.get("params"), dict) else {}
        fail_ids = set(params.get("fail_candidate_ids", config.get("fail_candidate_ids", [])))
        if candidate.candidate_id in fail_ids:
            from protein_design.core.exceptions import ValidationError
            raise ValidationError(
                f"Simulated validator failure for candidate {candidate.candidate_id}",
                candidate_id=candidate.candidate_id,
            )

        metrics = candidate.metrics

        # Structure QC based on pLDDT
        structure_qc = self._check_metric(
            metrics, config, "plddt", "structure_quality", "higher_better"
        )

        # Interface QC based on ipTM
        interface_qc = self._check_metric(
            metrics, config, "iptm", "interface_quality", "higher_better"
        )

        # Developability based on sequence length (dummy check)
        dev_passed = True
        dev_metric_value = float(candidate.length)
        developability_qc = QCResult(
            passed=dev_passed,
            metric_name="sequence_length",
            metric_value=dev_metric_value,
            details={"check": "dummy_developability"},
        )

        # Novelty (always novel in dummy mode)
        novelty_qc = QCResult(
            passed=True,
            metric_name="novelty",
            metric_value=1.0,
            details={"check": "dummy_novelty", "is_novel": True},
        )

        overall = all(
            qc.passed
            for qc in [structure_qc, interface_qc, developability_qc, novelty_qc]
            if qc is not None
        )

        return ValidationResult(
            sequence_qc=QCResult(
                passed=True,
                metric_name="sequence_validity",
                metric_value=1.0,
                details={"check": "dummy_sequence_qc"},
            ),
            structure_qc=structure_qc,
            interface_qc=interface_qc,
            developability_qc=developability_qc,
            novelty_qc=novelty_qc,
            overall_passed=overall,
        )

    def _check_metric(
        self,
        metrics: dict[str, Any],
        config: dict[str, Any],
        metric_key: str,
        check_name: str,
        direction: str = "higher_better",
    ) -> QCResult:
        """Check a single metric against its configured threshold.

        If threshold is None, the check always passes.
        """
        metric_config = config.get(metric_key, {})
        threshold = metric_config.get("threshold") if isinstance(metric_config, dict) else None
        enabled = metric_config.get("enabled", True) if isinstance(metric_config, dict) else True

        value = metrics.get(metric_key)
        if value is None:
            return QCResult(
                passed=True,
                metric_name=check_name,
                details={"reason": f"metric '{metric_key}' not available, skipped"},
            )

        if not enabled or threshold is None:
            # Metric computed but not filtered
            return QCResult(
                passed=True,
                metric_name=check_name,
                metric_value=float(value),
                threshold=threshold,
                details={"reason": "threshold not calibrated, check skipped"},
            )

        if direction == "higher_better":
            passed = float(value) >= threshold
        else:
            passed = float(value) <= threshold

        return QCResult(
            passed=passed,
            metric_name=check_name,
            metric_value=float(value),
            threshold=threshold,
            details={"direction": direction},
        )
