"""Abstract Predictor interface.

All structure predictors must implement this interface.

Future implementations:
    AlphaFold2Predictor
    RF3Predictor
    ChaiPredictor
    ColabFoldPredictor
    ESMFoldPredictor
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, Field

from protein_design.schemas import Candidate, Target


class PredictionResult(BaseModel):
    """Result from a structure prediction."""
    metrics: dict[str, Any] = Field(default_factory=dict)
    structure_content: Optional[str] = None  # CIF/PDB content as string
    complex_content: Optional[str] = None    # Complex CIF/PDB content
    confidence: Optional[float] = None


class BasePredictor(ABC):
    """Abstract base class for structure predictors."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Predictor name (e.g., 'alphafold2', 'chai')."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Predictor version string."""
        ...

    @abstractmethod
    def predict(
        self,
        candidate: Candidate,
        target: Target,
        config: dict[str, Any],
    ) -> PredictionResult:
        """Predict structure for a candidate-target complex.

        Args:
            candidate: The candidate binder.
            target: The protein target.
            config: Predictor-specific configuration.

        Returns:
            PredictionResult with metrics, structure content, etc.
        """
        ...
