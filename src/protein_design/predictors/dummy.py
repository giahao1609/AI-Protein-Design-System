"""Dummy Predictor — Produces fake structure predictions for pipeline testing."""

from __future__ import annotations

import random
from typing import Any

from protein_design.predictors.base import BasePredictor, PredictionResult
from protein_design.schemas import Candidate, Target


class DummyPredictor(BasePredictor):
    """Generates fake prediction metrics for testing."""

    @property
    def name(self) -> str:
        return "dummy"

    @property
    def version(self) -> str:
        return "1.0.0"

    def predict(
        self,
        candidate: Candidate,
        target: Target,
        config: dict[str, Any],
    ) -> PredictionResult:
        """Generate fake pLDDT, pTM, ipTM scores and placeholder structures.

        Uses candidate seed for deterministic fake scores.
        """
        params = config.get("params", {}) if isinstance(config.get("params"), dict) else {}
        fail_ids = set(params.get("fail_candidate_ids", config.get("fail_candidate_ids", [])))
        timeout_ids = set(params.get("timeout_candidate_ids", config.get("timeout_candidate_ids", [])))

        if candidate.candidate_id in fail_ids:
            from protein_design.core.exceptions import PredictionError
            raise PredictionError(
                f"Simulated predictor failure for candidate {candidate.candidate_id}",
                candidate_id=candidate.candidate_id,
            )

        if candidate.candidate_id in timeout_ids:
            raise TimeoutError(f"Simulated predictor timeout for candidate {candidate.candidate_id}")

        rng = random.Random(candidate.seed or 42)

        plddt = round(rng.uniform(50.0, 95.0), 2)
        ptm = round(rng.uniform(0.3, 0.95), 3)
        iptm = round(rng.uniform(0.2, 0.9), 3)
        pae = round(rng.uniform(2.0, 25.0), 2)

        # Fake CIF content
        structure_content = (
            f"# Dummy structure for {candidate.candidate_id}\n"
            f"# pLDDT={plddt}, pTM={ptm}, ipTM={iptm}\n"
            f"# Sequence: {candidate.sequence[:20]}...\n"
            f"data_{candidate.candidate_id}\n"
            f"_entry.id {candidate.candidate_id}\n"
        )

        complex_content = (
            f"# Dummy complex for {candidate.candidate_id} + {target.target_id}\n"
            f"# ipTM={iptm}, pAE={pae}\n"
            f"data_{candidate.candidate_id}_complex\n"
            f"_entry.id {candidate.candidate_id}_complex\n"
        )

        return PredictionResult(
            metrics={
                "plddt": plddt,
                "ptm": ptm,
                "iptm": iptm,
                "pae": pae,
            },
            structure_content=structure_content,
            complex_content=complex_content,
            confidence=iptm,
        )
