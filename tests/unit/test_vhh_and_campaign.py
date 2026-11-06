"""Unit tests for VHH Scaffold Generator and Competition Campaign Runner."""

from __future__ import annotations


from protein_design.core.campaign import CompetitionCampaignRunner
from protein_design.generators.vhh import VHHScaffoldGenerator
from protein_design.schemas import Target
from protein_design.storage.artifacts import ArtifactStore
from protein_design.storage.database import MetadataStore


def test_vhh_scaffold_generator(tmp_path):
    """Test VHHScaffoldGenerator produces valid 100-150 aa antibodies with 2 Cysteines."""
    target = Target(
        target_id="EGFR",
        name="EGFR",
        source="competition",
        sequence="ACDEFGHIKLMNPQRSTVWY" * 5,
        metadata={"ph_condition": 6.0, "molecule_type": "VHH"},
    )

    gen = VHHScaffoldGenerator()
    config = {"design_path": str(tmp_path / "artifacts")}
    candidates = gen.generate(target=target, config=config, num_candidates=5, seed=123)

    assert len(candidates) == 5
    for c in candidates:
        seq = c.sequence
        # 1. Length constraint 100-150 aa
        assert 100 <= len(seq) <= 150
        # 2. Exactly 2 canonical cysteines
        assert seq.count("C") == 2
        # 3. Only 20 natural amino acids
        assert set(seq).issubset(set("ACDEFGHIKLMNPQRSTVWY"))
        # 4. Nanobody35 defense
        assert c.metrics["nb35_cdr3_identity"] < 0.60
        # 5. Correct generator metadata
        assert c.generator == "vhh_scaffold"


def test_competition_campaign_runner(tmp_path):
    """Test end-to-end competition track campaign execution and submission package export."""
    db_path = tmp_path / "campaign_test.db"
    db = MetadataStore(db_path)
    db.initialize()
    artifacts = ArtifactStore(tmp_path / "artifacts")

    runner = CompetitionCampaignRunner(
        db=db,
        artifacts=artifacts,
        targets_dir="competition/targets",
    )

    # Execute track 1 (EGFR)
    result = runner.run_track_campaign(
        target_identifier="EGFR",
        num_candidates=3,
        mode="early_claim",
        output_dir=tmp_path / "submissions",
        seed=42,
    )

    assert result["target_id"] == "EGFR"
    assert result["molecule_type"] == "VHH"
    assert result["valid_candidates"] > 0
    assert len(result["top_candidates"]) > 0

    pkg = result["submission_package"]
    assert pkg["primary_csv"].exists()
    assert pkg["update_note_file"].exists()
    assert pkg["methods_abstract_file"].exists()

    # Check persistence in database
    cands_in_db = db.list_candidates(target_id="EGFR")
    assert len(cands_in_db) > 0
    history = db.get_submission_history(target_name="EGFR")
    assert len(history) == 1
    assert history[0]["mode"] == "early_claim"
