"""Abstract Validator interface.

All validators must implement this interface.
Thresholds come from CONFIG, not from Python code.

Future implementations:
    StructureValidator (clash score, Ramachandran)
    InterfaceValidator (contact area, shape complementarity)
    DevelopabilityValidator (solubility, aggregation)
    NoveltyValidator (BLAST, Foldseek search)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, Field

from protein_design.schemas import Candidate, QCResult


class ValidationResult(BaseModel):
    """Aggregate result from all validation checks."""
    sequence_qc: Optional[QCResult] = None
    structure_qc: Optional[QCResult] = None
    interface_qc: Optional[QCResult] = None
    developability_qc: Optional[QCResult] = None
    novelty_qc: Optional[QCResult] = None
    overall_passed: bool = True
    details: dict[str, Any] = Field(default_factory=dict)


class BaseValidator(ABC):
    """Abstract base class for candidate validators."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Validator name."""
        ...

    @abstractmethod
    def validate(
        self,
        candidate: Candidate,
        config: dict[str, Any],
    ) -> ValidationResult:
        """Run all validation checks on a candidate.

        Thresholds MUST come from config, not hardcoded.
        If a threshold is None/null in config, the metric is computed
        but NOT used for filtering.

        Args:
            candidate: The candidate to validate.
            config: Validation configuration with thresholds.

        Returns:
            ValidationResult with QC results for each check.
        """
        ...
