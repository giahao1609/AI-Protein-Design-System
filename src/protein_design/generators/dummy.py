"""Dummy Generator — Produces fake candidates for pipeline testing.

This generator creates random amino acid sequences.
It exists to verify the entire pipeline works end-to-end
before integrating real protein models.
"""

from __future__ import annotations

import random
from typing import Any

from protein_design.generators.base import BaseGenerator
from protein_design.schemas import Candidate, Target, DesignType, generate_sequential_id


# Standard amino acids
AMINO_ACIDS = "ACDEFGHIKLMNPQRSTVWY"


class DummyGenerator(BaseGenerator):
    """Generates random amino acid sequences for testing."""

    @property
    def name(self) -> str:
        return "dummy"

    @property
    def version(self) -> str:
        return "1.0.0"

    def generate(
        self,
        target: Target,
        config: dict[str, Any],
        num_candidates: int = 10,
        seed: int = 42,
    ) -> list[Candidate]:
        """Generate N random amino acid sequences.

        Config options:
            min_length (int): Minimum sequence length (default: 40)
            max_length (int): Maximum sequence length (default: 80)
            design_type (str): Design type (default: 'minibinder')
        """
        rng = random.Random(seed)
        min_length = config.get("min_length", 40)
        max_length = config.get("max_length", 80)
        design_type_str = config.get("design_type", "minibinder")

        try:
            design_type = DesignType(design_type_str)
        except ValueError:
            design_type = DesignType.OTHER

        candidates = []
        for i in range(num_candidates):
            length = rng.randint(min_length, max_length)
            sequence = "".join(rng.choices(AMINO_ACIDS, k=length))
            candidate_seed = seed + i

            candidate = Candidate(
                candidate_id=generate_sequential_id("cand", i + 1),
                target_id=target.target_id,
                sequence=sequence,
                design_type=design_type,
                generator=self.name,
                generator_version=self.version,
                seed=candidate_seed,
            )
            candidates.append(candidate)

        return candidates
