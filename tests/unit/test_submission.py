"""Unit tests for competition submission package export and rolling claims."""

from __future__ import annotations

import csv

import pytest

from protein_design.core.exceptions import SecurityIntegrityError
from protein_design.export.submission import (
    generate_submission_package,
    validate_sequence_for_submission,
)
from protein_design.predictors.esmfold_ipsae import (
    ESMFold2_ipSAE_Scorer,
)
from protein_design.schemas import Candidate, Target
from protein_design.storage.database import MetadataStore
from protein_design.validation.druggability import (
    check_druggability,
    verify_anti_collision,
)


def test_validate_sequence_rules():
    """Verify sequence validation for amino acids, length, and prohibited tags."""
    # Valid minibinder (60 aa)
    valid_seq = "ACDEFGHIKLMNPQRSTVWY" * 3
    validate_sequence_for_submission(valid_seq, molecule_type="minibinder")

    # Invalid character (e.g. 'B' or 'X')
    with pytest.raises(SecurityIntegrityError, match="invalid/non-standard characters"):
        validate_sequence_for_submission("ACDEFGHIKLMNPQRSTVWX" * 3, molecule_type="minibinder")

    # Length violation (minibinder < 40)
    with pytest.raises(SecurityIntegrityError, match="outside valid range"):
        validate_sequence_for_submission("ACDEFGHIKLMNPQRSTVWY", molecule_type="minibinder")

    # Purification tags
    with pytest.raises(SecurityIntegrityError, match="His6-tag"):
        validate_sequence_for_submission("HHHHHH" + "ACDEFGHIKLMNPQRSTVWY" * 2)

    with pytest.raises(SecurityIntegrityError, match="Flag-tag"):
        validate_sequence_for_submission("DYKDDDDK" + "ACDEFGHIKLMNPQRSTVWY" * 2)

    with pytest.raises(SecurityIntegrityError, match="Myc-tag"):
        validate_sequence_for_submission("EQKLISEEDL" + "ACDEFGHIKLMNPQRSTVWY" * 2)

    with pytest.raises(SecurityIntegrityError, match="Strep-tag"):
        validate_sequence_for_submission("WSHPQFEK" + "ACDEFGHIKLMNPQRSTVWY" * 2)

    with pytest.raises(SecurityIntegrityError, match="redundant terminal GS linker"):
        validate_sequence_for_submission("GGGGS" + "ACDEFGHIKLMNPQRSTVWY" * 2)


def test_generate_submission_rolling_and_fallback(tmp_path):
    """Verify rolling claim mode, fallback CSV generation, notes, and abstract."""
    real_struct = tmp_path / "structure.cif"
    real_struct.write_text("data_test\n_entry.id 1\n")

    # Valid 118 aa VHH sequence for TNF-α (Track 2 is official VHH, 100-150 aa)
    vhh_seq = (
        "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKDRLSGHYWGQGTLVTVSS"
    )
    candidates = [
        Candidate(
            candidate_id=f"cand_{i+1:03d}",
            target_id="TNF-α",
            sequence=vhh_seq,
            generator="vhh_scaffold",
            generator_version="1.0.0-competition",
            structure_path=real_struct,
            metadata={"validation_history": ["RosettaFastRelax"]},
        )
        for i in range(5)
    ]

    # Run in early_claim mode
    pkg = generate_submission_package(
        candidates=candidates,
        target_name="TNF-α",
        output_dir=tmp_path / "submissions",
        molecule_type="VHH",
        mode="early_claim",
        generate_ascii_fallback=True,
    )

    assert pkg["mode"] == "early_claim"
    assert pkg["version_tag"] == "v1.0_early_claim"

    # 1. Primary Unicode CSV
    primary_csv = pkg["primary_csv"]
    assert primary_csv.name == "TNF-α_submission.csv"
    assert primary_csv.exists()

    with open(primary_csv, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == ["name", "sequence"]
        rows = list(reader)
        assert len(rows) == 5
        assert rows[0][0] == "TNF-α_des_01"

    # 2. ASCII Fallback CSV
    fallback_csv = pkg["fallback_csv"]
    assert fallback_csv is not None
    assert fallback_csv.name == "TNF-a_submission.csv"
    assert fallback_csv.exists()

    # 3. Notes and Abstract
    note_file = pkg["update_note_file"]
    abstract_file = pkg["methods_abstract_file"]
    assert note_file.exists()
    assert abstract_file.exists()
    assert "First-come, First-served" in note_file.read_text(encoding="utf-8")
    assert len(abstract_file.read_text(encoding="utf-8")) < 4000


def test_submission_history_in_sqlite(tmp_path):
    """Verify recording of submission attempts in SQLite MetadataStore."""
    db = MetadataStore(tmp_path / "test_sub.db")
    db.initialize()

    real_struct = tmp_path / "structure.cif"
    real_struct.write_text("data_test\n_entry.id 1\n")

    candidates = [
        Candidate(
            candidate_id="cand_hist_01",
            target_id="TL1A",
            sequence="ACDEFGHIKLMNPQRSTVWY" * 3,
            generator="bindcraft",
            generator_version="0.1.0-draft",
            structure_path=real_struct,
            metadata={"validation_history": ["RosettaFastRelax"]},
        )
    ]

    pkg = generate_submission_package(
        candidates=candidates,
        target_name="TL1A",
        output_dir=tmp_path / "out",
        mode="early_claim",
        db=db,
    )

    history = db.get_submission_history(target_name="TL1A")
    assert len(history) == 1
    assert history[0]["submission_id"] == pkg["submission_id"]
    assert history[0]["version_tag"] == "v1.0_early_claim"
    assert "cand_hist_01" in history[0]["candidate_ids"]


def test_druggability_and_anti_collision():
    """Verify druggability liabilities check and pairwise anti-collision."""
    # 1. Unpaired cysteines in minibinder (no C in base, plus 1 C = 1 Cysteine)
    odd_cys_seq = "ADEFGHIKLMNPQRSTVW" * 3 + "C"
    res = check_druggability(odd_cys_seq, molecule_type="minibinder")
    assert res["cysteine_count"] == 1
    assert res["unpaired_cysteines"] is True
    assert res["passed"] is False

    # 2. Glycosylation motif (N-X-S/T where X != P)
    glyc_seq = "ACDEFGHIKLMNPQRSTVWY" + "NAS" + "ACDEFGHIKLMNPQRSTVWY"
    res_glyc = check_druggability(glyc_seq, molecule_type="minibinder")
    assert res_glyc["glycosylation_sites"] > 0
    assert res_glyc["passed"] is False

    # 3. Anti-collision check for minibinder
    base_seq = "ACDEFGHIKLMNPQRSTVWY" * 3
    identical_variant = base_seq[:58] + "AA"  # > 85% identical
    with pytest.raises(SecurityIntegrityError, match="exceeds 85% diversity ceiling"):
        verify_anti_collision(
            candidate_seq=identical_variant,
            pool_sequences=[base_seq],
            molecule_type="minibinder",
        )


def test_esmfold_ipsae_scorer():
    """Verify ESMFold2 + ipSAE scoring engine produces expected metric keys."""
    scorer = ESMFold2_ipSAE_Scorer(
        num_seeds=1,
        num_samples=1,
        use_templates=False,
        target_msa=True,
        design_msa=False,
    )

    cand = Candidate(
        candidate_id="cand_esm_01",
        target_id="EGFR",
        sequence="ACDEFGHIKLMNPQRSTVWY" * 3,
        generator="bindcraft",
        generator_version="0.1.0-draft",
    )
    target = Target(
        target_id="EGFR",
        name="EGFR",
        source="test",
        sequence="ACDEFGHIKLMNPQRSTVWY" * 5,
    )

    result = scorer.predict(candidate=cand, target=target, config={})
    m = result.metrics
    assert "esmfold_plddt" in m
    assert "esmfold_pae_interface" in m
    assert "ipsae_score" in m
    assert m["target_msa_used"] is True
    assert m["design_msa_used"] is False
    assert 0.0 <= m["ipsae_score"] <= 1.0


def test_nanobody35_blacklist_and_multischeme_collision():
    """Verify Nanobody35 hard blacklist rejection and multi-scheme collision checks."""
    from protein_design.validation.druggability import (
        NANOBODY_35_SEQUENCE,
        extract_vhh_cdrs_all_schemes,
    )

    # 1. Multi-scheme extraction check
    schemes = extract_vhh_cdrs_all_schemes(NANOBODY_35_SEQUENCE)
    assert set(schemes.keys()) == {"imgt", "kabat", "chothia", "abm"}
    for s in ("imgt", "kabat", "chothia", "abm"):
        assert "cdr1" in schemes[s]
        assert "cdr2" in schemes[s]
        assert "cdr3" in schemes[s]

    # 2. Nanobody35 hard blacklist rejection
    with pytest.raises(SecurityIntegrityError, match="Disqualification Risk: Candidate .* Nanobody35"):
        verify_anti_collision(
            candidate_seq=NANOBODY_35_SEQUENCE,
            pool_sequences=[],
            molecule_type="vhh",
            candidate_id="cand_nb35_mimic",
        )

    # 3. Multi-scheme CDR collision check between two identical VHHs
    mock_vhh = (
        "EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKG"
        "RFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKDGYYGNYDYWGQGTLVTVSS"
    )
    with pytest.raises(SecurityIntegrityError, match="Anti-collision violation .* Identical CDRs"):
        verify_anti_collision(
            candidate_seq=mock_vhh,
            pool_sequences=[mock_vhh],
            molecule_type="vhh",
            candidate_id="cand_vhh_dup",
        )


def test_advanced_druggability_and_masking():
    """Verify advanced biophysical developability gates and signal peptide masking."""
    from protein_design.predictors.esmfold_ipsae import compute_ipsae_score
    from protein_design.validation.druggability import (
        calculate_isoelectric_point,
        calculate_net_charge,
    )

    seq = "ACDEFGHIKLMNPQRSTVWY" * 3
    pi = calculate_isoelectric_point(seq)
    charge_74 = calculate_net_charge(seq, ph=7.4)
    assert 4.0 <= pi <= 10.0
    assert -10.0 <= charge_74 <= 10.0

    # Test charge run rejection (e.g. KKKK)
    charge_run_seq = "ACDEFGHIKLMNPQRSTVWY" + "KKKK" + "ACDEFGHIKLMNPQRSTVWY"
    res_run = check_druggability(charge_run_seq, molecule_type="minibinder")
    assert len(res_run["charge_runs"]) > 0
    assert res_run["passed"] is False

    # Test hydrophobic patch rejection (e.g. LLLLV)
    patch_seq = "ACDEFGHIKLMNPQRSTVWY" + "LLLLV" + "ACDEFGHIKLMNPQRSTVWY"
    res_patch = check_druggability(patch_seq, molecule_type="minibinder")
    assert len(res_patch["hydrophobic_patches"]) > 0
    assert res_patch["passed"] is False

    # Test signal peptide masking calculation
    unmasked_score = compute_ipsae_score(plddt=85.0, interface_pae=6.0, interface_contacts=20, masked_contacts_count=0)
    masked_score = compute_ipsae_score(plddt=85.0, interface_pae=6.0, interface_contacts=20, masked_contacts_count=15)
    assert unmasked_score > masked_score

