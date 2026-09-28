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
        params = config.get("params", {}) if isinstance(config.get("params"), dict) else {}
        if params.get("fail_generation", config.get("fail_generation", False)):
            from protein_design.core.exceptions import GenerationError
            raise GenerationError("Simulated generator crash", candidate_id=None)

        rng = random.Random(seed)
        min_length = params.get("min_length", config.get("min_length", 40))
        max_length = params.get("max_length", config.get("max_length", 80))
        design_type_str = params.get("design_type", config.get("design_type", "minibinder"))
        duplicate_indices = set(params.get("duplicate_indices", config.get("duplicate_indices", [])))

        try:
            design_type = DesignType(design_type_str)
        except ValueError:
            design_type = DesignType.OTHER

        candidates = []
        first_sequence = ""

        for i in range(num_candidates):
            if i in duplicate_indices and first_sequence:
                sequence = first_sequence
            else:
                length = rng.randint(min_length, max_length)
                sequence = "".join(rng.choices(AMINO_ACIDS, k=length))
                if not first_sequence:
                    first_sequence = sequence

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
