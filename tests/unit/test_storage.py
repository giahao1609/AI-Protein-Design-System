"""Unit tests for storage layer (SQLite + filesystem)."""

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
    Target,
)
from protein_design.storage.database import MetadataStore
from protein_design.storage.artifacts import ArtifactStore


class TestMetadataStore:
    def test_save_and_get_target(self, db, sample_target):
        db.save_target(sample_target)
        loaded = db.get_target(sample_target.target_id)
        assert loaded is not None
        assert loaded.name == sample_target.name
        assert loaded.sequence == sample_target.sequence

    def test_list_targets(self, db, sample_target):
        db.save_target(sample_target)
        targets = db.list_targets()
        assert len(targets) == 1
        assert targets[0].target_id == sample_target.target_id

    def test_save_and_get_candidate(self, db, sample_target, sample_candidate):
        db.save_target(sample_target)
        db.save_candidate(sample_candidate)
        loaded = db.get_candidate(sample_candidate.candidate_id)
        assert loaded is not None
        assert loaded.sequence == sample_candidate.sequence
        assert loaded.status == CandidateStatus.CREATED

    def test_list_candidates_with_filter(self, db, sample_target):
        db.save_target(sample_target)

        for i in range(5):
            cand = Candidate(
                candidate_id=f"cand_{i:06d}",
                target_id=sample_target.target_id,
                sequence=f"ACDEF{'G' * (i + 10)}",
                generator="test",
                generator_version="1.0",
            )
            if i % 2 == 0:
                cand.transition(CandidateStatus.GENERATED, "test", "gen")
            db.save_candidate(cand)

        all_cands = db.list_candidates(target_id=sample_target.target_id)
        assert len(all_cands) == 5

        generated = db.list_candidates(status="GENERATED")
        assert len(generated) == 3  # 0, 2, 4

    def test_count_candidates(self, db, sample_target, sample_candidate):
        db.save_target(sample_target)
        db.save_candidate(sample_candidate)
        assert db.count_candidates() == 1
        assert db.count_candidates(target_id=sample_target.target_id) == 1
        assert db.count_candidates(target_id="nonexistent") == 0

    def test_candidate_dedup_by_hash(self, db, sample_target, sample_candidate):
        db.save_target(sample_target)
        db.save_candidate(sample_candidate)
        assert db.candidate_exists_by_hash(sample_candidate.sequence_hash)
        assert not db.candidate_exists_by_hash("nonexistent_hash")

    def test_save_and_get_run(self, db, sample_target):
        db.save_target(sample_target)
        run = ExperimentRun(target_id=sample_target.target_id)
        db.save_run(run)
        loaded = db.get_run(run.run_id)
        assert loaded is not None
        assert loaded.target_id == sample_target.target_id

    def test_save_evidence(self, db):
        evi = EvidenceRecord(
            claim="Test claim",
            source_type="test",
            source="test source",
            evidence_level=EvidenceLevel.PEER_REVIEWED,
        )
        db.save_evidence(evi)
        loaded = db.get_evidence(evi.evidence_id)
        assert loaded is not None
        assert loaded.claim == "Test claim"

    def test_save_decision_never_overwrite(self, db):
        dec1 = DecisionRecord(
            question="Q1",
            claim="C1",
            decision="D1",
            confidence=0.8,
            author="test",
        )
        db.save_decision(dec1)

        dec2 = DecisionRecord(
            question="Q1",
            claim="C1 revised",
            decision="D2",
            confidence=0.9,
            author="test",
            supersedes=dec1.decision_id,
        )
        db.save_decision(dec2)

        decisions = db.list_decisions()
        assert len(decisions) == 2  # Both preserved


class TestArtifactStore:
    def test_save_sequence(self, artifacts):
        path = artifacts.save_sequence("tgt_001", "cand_001", "ACDEFG", "test")
        assert path.exists()
        content = path.read_text()
        assert ">cand_001" in content
        assert "ACDEFG" in content

    def test_save_structure(self, artifacts):
        path = artifacts.save_structure("tgt_001", "cand_001", "DUMMY CIF", "binder.cif")
        assert path.exists()
        assert path.read_text() == "DUMMY CIF"

    def test_save_provenance(self, artifacts):
        path = artifacts.save_provenance("tgt_001", "cand_001", {"key": "value"})
        assert path.exists()

    def test_candidate_dir_structure(self, artifacts):
        artifacts.save_sequence("tgt_001", "cand_042", "ACDEFG")
        d = artifacts.candidate_dir("tgt_001", "cand_042")
        assert d.exists()
        assert (d / "sequence.fasta").exists()

    def test_artifact_exists(self, artifacts):
        artifacts.save_sequence("tgt_001", "cand_001", "ACDEFG")
        assert artifacts.candidate_artifact_exists("tgt_001", "cand_001", "sequence.fasta")
        assert not artifacts.candidate_artifact_exists("tgt_001", "cand_001", "missing.file")
