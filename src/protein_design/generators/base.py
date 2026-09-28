"""Abstract Generator interface.

All protein generators must implement this interface.
No model-specific code belongs here.

Future implementations:
    BindCraftGenerator
    RFdiffusionGenerator
    VHHGenerator
    ProteinMPNNSequenceDesigner
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from protein_design.schemas import Candidate, Target


class BaseGenerator(ABC):
    """Abstract base class for protein binder generators.

    Generators produce candidate sequences (and optionally structures)
    given a target protein and configuration.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Generator name (e.g., 'bindcraft', 'rfdiffusion')."""
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """Generator version string."""
        ...

    @abstractmethod
    def generate(
        self,
        target: Target,
        config: dict[str, Any],
        num_candidates: int = 10,
        seed: int = 42,
    ) -> list[Candidate]:
        """Generate candidate protein binders.

        Args:
            target: The protein target.
            config: Generator-specific configuration.
            num_candidates: Number of candidates to generate.
            seed: Random seed for reproducibility.

        Returns:
            List of Candidate objects with sequences populated.
            Each candidate should have:
                - candidate_id
                - target_id
                - sequence
                - design_type
                - generator (= self.name)
                - generator_version (= self.version)
                - seed
                - status = CREATED
        """
        ...

    def validate_config(self, config: dict[str, Any]) -> None:
        """Validate generator-specific configuration.

        Override in subclasses to add validation.
        Raises ConfigError if invalid.
        """
        pass
