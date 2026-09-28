"""Unit tests for Pydantic schemas."""

from __future__ import annotations

import pytest

from protein_design.schemas import (
    Candidate,
    CandidateStatus,
    DecisionRecord,
    DesignType,
    EvidenceLevel,
    EvidenceRecord,
    ExperimentRun,
    ScientificStatus,
    Target,
)
from protein_design.schemas.common import (
    QCResult,
    StatusTransition,
    generate_id,
    generate_sequential_id,
    hash_string,
    hash_dict,
)


class TestTarget:
    def test_create_target(self):
        target = Target(
            name="Test Target",
            source="test",
            sequence="MKTVRQERLKSIVRILERSKEPV",
            source_references=["PDB:1ABC"],
        )
        assert target.target_id.startswith("tgt_")
        assert target.sequence_length == 23
        assert target.target_hash != ""
        assert len(target.target_hash) == 64  # SHA-256

    def test_target_hash_deterministic(self):
        seq = "MKTVRQERLKSIVRILERSKEPV"
        t1 = Target(name="A", source="test", sequence=seq)
        t2 = Target(name="B", source="test", sequence=seq)
        assert t1.target_hash == t2.target_hash

    def test_target_hash_changes_with_sequence(self):
        t1 = Target(name="A", source="test", sequence="MKTV")
        t2 = Target(name="A", source="test", sequence="ACDE")
        assert t1.target_hash != t2.target_hash


class TestCandidate:
    def test_create_candidate(self):
        cand = Candidate(
            target_id="tgt_001",
            sequence="ACDEFGHIKLMNPQRSTVWY",
            generator="test",
            generator_version="1.0",
        )
        assert cand.candidate_id.startswith("cand_")
        assert cand.length == 20
        assert cand.sequence_hash != ""
        assert cand.status == CandidateStatus.CREATED
        assert cand.scientific_status == ScientificStatus.GENERATED

    def test_sequence_hash_deterministic(self):
        seq = "ACDEFGHIKLMNPQRSTVWY"
        c1 = Candidate(target_id="t", sequence=seq, generator="g", generator_version="1")
        c2 = Candidate(target_id="t", sequence=seq, generator="g", generator_version="1")
        assert c1.sequence_hash == c2.sequence_hash

    def test_transition(self):
        cand = Candidate(
            target_id="tgt_001",
            sequence="ACDEFGHIKLMNPQRSTVWY",
            generator="test",
            generator_version="1.0",
        )
        cand.transition(
            CandidateStatus.GENERATED,
            reason="test",
            stage="generation",
        )
        assert cand.status == CandidateStatus.GENERATED
        assert len(cand.status_history) == 1
        assert cand.status_history[0].from_status == CandidateStatus.CREATED
        assert cand.status_history[0].to_status == CandidateStatus.GENERATED

    def test_multiple_transitions(self):
        cand = Candidate(
            target_id="tgt_001",
            sequence="ACDEFGHIKLMNPQRSTVWY",
            generator="test",
            generator_version="1.0",
        )
        cand.transition(CandidateStatus.GENERATED, "gen", "generation")
        cand.transition(CandidateStatus.REJECTED, "bad score", "validation", "plddt", 45.0, 70.0)

        assert cand.status == CandidateStatus.REJECTED
        assert len(cand.status_history) == 2
        assert cand.status_history[1].metric_name == "plddt"
        assert cand.status_history[1].metric_value == 45.0
        assert cand.status_history[1].threshold == 70.0


class TestExperimentRun:
    def test_create_run(self):
        run = ExperimentRun(target_id="tgt_001")
        assert run.run_id.startswith("run_")
        assert run.status.value == "PENDING"

    def test_run_lifecycle(self):
        run = ExperimentRun(target_id="tgt_001")
        run.mark_started()
        assert run.status.value == "RUNNING"
        run.mark_completed({"total": 10})
        assert run.status.value == "COMPLETED"
        assert run.finished_at is not None
        assert run.output_summary["total"] == 10

    def test_run_add_candidate(self):
        run = ExperimentRun(target_id="tgt_001")
        run.add_candidate("cand_001")
        run.add_candidate("cand_002")
        assert len(run.candidate_ids) == 2


class TestEvidenceRecord:
    def test_create_evidence(self):
        evi = EvidenceRecord(
            claim="Protein X binds target Y",
            source_type="paper",
            source="Smith et al. 2024",
            doi="10.1234/test",
            evidence_level=EvidenceLevel.PEER_REVIEWED,
        )
        assert evi.evidence_id.startswith("evi_")
        assert evi.evidence_level == EvidenceLevel.PEER_REVIEWED
        assert evi.evidence_level.value == 3

    def test_evidence_hierarchy(self):
        assert EvidenceLevel.EXPERIMENTAL_WETLAB.value < EvidenceLevel.AI_REASONING.value
        assert EvidenceLevel.PEER_REVIEWED.value < EvidenceLevel.PREPRINT.value


class TestDecisionRecord:
    def test_create_decision(self):
        dec = DecisionRecord(
            question="Should we use threshold X?",
            claim="Threshold X is optimal",
            decision="Use threshold X after benchmarking",
            confidence=0.8,
            author="researcher",
        )
        assert dec.decision_id.startswith("dec_")
        assert 0.0 <= dec.confidence <= 1.0

    def test_decision_confidence_bounds(self):
        with pytest.raises(Exception):
            DecisionRecord(
                question="Q",
                claim="C",
                decision="D",
                confidence=1.5,  # Out of bounds
                author="test",
            )


class TestUtilities:
    def test_generate_id(self):
        id1 = generate_id("test")
        id2 = generate_id("test")
        assert id1.startswith("test_")
        assert id1 != id2  # Unique

    def test_sequential_id(self):
        assert generate_sequential_id("cand", 1) == "cand_000001"
        assert generate_sequential_id("cand", 42) == "cand_000042"

    def test_hash_string(self):
        h1 = hash_string("hello")
        h2 = hash_string("hello")
        h3 = hash_string("world")
        assert h1 == h2
        assert h1 != h3
        assert len(h1) == 64

    def test_hash_dict(self):
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 2, "a": 1}  # Different order, same content
        assert hash_dict(d1) == hash_dict(d2)  # Sort-stable
