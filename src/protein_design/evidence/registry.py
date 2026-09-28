"""Evidence registry — Manage evidence and decision records.

Every scientific assumption must have a source.
AI reasoning is ranked LAST in the evidence hierarchy.
"""

from __future__ import annotations

from typing import Optional

from protein_design.schemas import DecisionRecord, EvidenceLevel, EvidenceRecord
from protein_design.storage.database import MetadataStore
from protein_design.logging import get_logger

log = get_logger(module="evidence.registry")


class EvidenceRegistry:
    """Manages evidence and decision records in the metadata store."""

    def __init__(self, db: MetadataStore):
        self.db = db

    def add_evidence(self, evidence: EvidenceRecord) -> None:
        """Add an evidence record."""
        self.db.save_evidence(evidence)
        log.info(
            "evidence_added",
            evidence_id=evidence.evidence_id,
            claim=evidence.claim,
            level=evidence.evidence_level.name,
        )

    def add_decision(self, decision: DecisionRecord) -> None:
        """Add a decision record. Never overwrites previous decisions."""
        self.db.save_decision(decision)
        log.info(
            "decision_added",
            decision_id=decision.decision_id,
            question=decision.question,
            decision=decision.decision,
            supersedes=decision.supersedes,
        )

    def get_evidence_for_claim(self, claim: str) -> list[EvidenceRecord]:
        """Find all evidence related to a claim."""
        return self.db.list_evidence(claim=claim)

    def get_decision_history(self) -> list[DecisionRecord]:
        """Get all decisions in chronological order."""
        return self.db.list_decisions()

    def get_latest_decision(self, question: str) -> Optional[DecisionRecord]:
        """Get the latest decision for a question.

        Looks for the most recent decision that hasn't been superseded.
        """
        all_decisions = self.db.list_decisions()
        superseded_ids = {
            d.supersedes for d in all_decisions if d.supersedes
        }

        matching = [
            d
            for d in all_decisions
            if d.question == question and d.decision_id not in superseded_ids
        ]

        if not matching:
            return None
        return matching[-1]
