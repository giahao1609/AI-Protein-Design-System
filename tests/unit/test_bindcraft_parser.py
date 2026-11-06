"""Tier A Unit Tests: BindCraft Output Parsing and Serialization.

Validates schema correctness, exact numeric extraction, mmCIF format conversion,
rejection counter ingestion, and error handling without asserting biological
thresholds (pLDDT > 80) or requiring GPU compute.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from protein_design.core.exceptions import GenerationError
from protein_design.generators.bindcraft import (
    convert_pdb_to_mmcif,
    parse_bindcraft_output,
    serialize_target_settings,
)
from protein_design.schemas import CandidateStatus, ScientificStatus, Target
from protein_design.schemas.common import ChainInfo, HotspotInfo


FIXTURES_DIR = Path("tests/fixtures/bindcraft_output")


def test_target_settings_serialization(tmp_path):
    """Verify target settings JSON contains exactly the 7 upstream verified keys."""
    target_seq = "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLA"
    target = Target(
        target_id="test_egfr",
        name="EGFR Ectodomain",
        source="literature",
        sequence=target_seq,
        chains=[
            ChainInfo(
                chain_id="A",
                sequence=target_seq,
                length=len(target_seq),
                description="Target chain",
            )
        ],
        hotspots=[
            HotspotInfo(chain_id="A", residue=120),
            HotspotInfo(chain_id="A", residue=124),
        ],
    )

    settings = serialize_target_settings(
        target=target,
        config={"binder_lengths": [55, 65]},
        output_dir=tmp_path / "output",
        num_candidates=5,
    )

    expected_keys = {
        "design_path",
        "binder_name",
        "starting_pdb",
        "chains",
        "target_hotspot_residues",
        "lengths",
        "number_of_final_designs",
    }
    assert set(settings.keys()) == expected_keys
    assert settings["chains"] == "A"
    assert settings["target_hotspot_residues"] == "A120,A124"
    assert settings["lengths"] == [55, 65]
    assert settings["number_of_final_designs"] == 5
    assert settings["binder_name"] == "test_egfr_binder"
    assert settings["design_path"] == str(tmp_path / "output")


def test_parse_valid_output_directory(tmp_path):
    """Verify parsing of valid mock BindCraft output directory with exact metric scales."""
    # Copy fixtures to tmp_path
    shutil.copytree(FIXTURES_DIR, tmp_path / "bindcraft_run")
    run_dir = tmp_path / "bindcraft_run"

    candidates, summary = parse_bindcraft_output(
        output_dir=run_dir,
        target_id="test_egfr",
    )

    assert len(candidates) == 2
    assert summary["total_parsed"] == 2

    c1 = candidates[0]
    assert c1.candidate_id == "cand_000001"
    assert c1.target_id == "test_egfr"
    assert c1.generator == "bindcraft"
    assert c1.generator_version == "0.1.0-draft"
    assert c1.seed == 412356
    assert c1.sequence == "MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGYVLA"
    assert c1.length == 63
    assert c1.status == CandidateStatus.GENERATED
    assert c1.scientific_status == ScientificStatus.GENERATED

    # Verify metrics schema and units
    m = c1.metrics
    # Raw pLDDT float (0.0-1.0) and transformed (0-100)
    assert m["raw_af2_plddt"] == pytest.approx(0.88, abs=1e-4)
    assert m["af2_plddt"] == pytest.approx(88.0, abs=1e-2)

    # Complex quality
    assert m["af2_ptm"] == pytest.approx(0.82, abs=1e-4)
    assert m["af2_iptm"] == pytest.approx(0.85, abs=1e-4)

    # Error metrics (normalized 0.0-1.0, not Angstroms)
    assert m["af2_pae"] == pytest.approx(0.18, abs=1e-4)
    assert m["af2_interface_pae"] == pytest.approx(0.22, abs=1e-4)

    # Physics metrics
    assert m["pyrosetta_interface_dg"] == pytest.approx(-42.5, abs=1e-2)  # In REU
    assert m["pyrosetta_interface_dsasa"] == pytest.approx(1420.5, abs=1e-1)  # In A^2
    assert m["pyrosetta_interface_sc"] == pytest.approx(0.68, abs=1e-3)
    assert m["pyrosetta_interface_packstat"] == pytest.approx(0.62, abs=1e-3)

    # Clashes
    assert m["unrelaxed_clashes"] == 1
    assert m["relaxed_clashes"] == 0

    # Model metrics preserved in metadata
    assert "model_metrics" in c1.metadata
    assert "1" in c1.metadata["model_metrics"]
    assert c1.metadata["model_metrics"]["1"]["pLDDT"] == pytest.approx(0.89, abs=1e-3)


def test_structure_format_conversion(tmp_path):
    """Verify structural conversion of PDB to mmCIF via gemmi."""
    import gemmi

    pdb_file = FIXTURES_DIR / "Accepted" / "target_binder_1.pdb"
    output_cif = tmp_path / "test_converted.cif"

    convert_pdb_to_mmcif(pdb_file, output_cif)

    assert output_cif.exists()
    assert output_cif.stat().st_size > 0

    # Verify converted file is valid mmCIF that gemmi can re-read
    doc = gemmi.cif.read_file(str(output_cif))
    assert len(doc) > 0
    block = doc.sole_block()
    # mmCIF contains standard categories
    assert block.find_loop("_atom_site.id") is not None


def test_parse_corrupted_scores_csv(tmp_path):
    """Verify error handling when scores CSV contains corrupted numeric data or missing columns."""
    corrupted_dir = tmp_path / "corrupted_run"
    corrupted_dir.mkdir(parents=True)

    # Missing 'Sequence' column entirely
    csv_file = corrupted_dir / "final_design_stats.csv"
    with open(csv_file, "w") as f:
        f.write("Design,Average_pLDDT\nbinder_1,0.85\n")

    with pytest.raises(GenerationError, match="missing canonical 'Sequence' column"):
        parse_bindcraft_output(output_dir=corrupted_dir, target_id="test_tgt")

    # Corrupted float metric
    with open(csv_file, "w") as f:
        f.write("Design,Sequence,Average_pLDDT\nbinder_1,ACDEFGH,not_a_number\n")

    with pytest.raises(GenerationError, match="Corrupted numeric metric"):
        parse_bindcraft_output(output_dir=corrupted_dir, target_id="test_tgt")


def test_parse_missing_scores_csv(tmp_path):
    """Verify error raising when final_design_stats.csv is missing."""
    empty_dir = tmp_path / "empty_run"
    empty_dir.mkdir(parents=True)

    with pytest.raises(GenerationError, match="Missing BindCraft score CSV"):
        parse_bindcraft_output(output_dir=empty_dir, target_id="test_tgt")


def test_parse_rejected_candidates_summary(tmp_path):
    """Verify rejection counters from failure_csv.csv are ingested into summary."""
    shutil.copytree(FIXTURES_DIR, tmp_path / "bindcraft_run")
    run_dir = tmp_path / "bindcraft_run"

    _, summary = parse_bindcraft_output(
        output_dir=run_dir,
        target_id="test_egfr",
    )

    rejections = summary["rejection_counts"]
    assert rejections["Trajectory"] == 12
    assert rejections["pLDDT"] == 45
    assert rejections["Contact_Loss"] == 8
    assert rejections["Clash"] == 15
    assert rejections["Rosetta_dG"] == 22


def test_duplicate_sequence_handling(tmp_path):
    """Verify that identical sequences are marked CandidateStatus.DUPLICATE."""
    run_dir = tmp_path / "dup_run"
    run_dir.mkdir(parents=True)

    csv_file = run_dir / "final_design_stats.csv"
    with open(csv_file, "w") as f:
        f.write("Design,Sequence,Average_pLDDT\n")
        f.write("binder_1,MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGY,0.88\n")
        f.write("binder_2,MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLRSLGYNIVATPRGY,0.86\n")

    candidates, _ = parse_bindcraft_output(output_dir=run_dir, target_id="test_tgt")
    assert len(candidates) == 2
    assert candidates[0].status == CandidateStatus.GENERATED
    assert candidates[1].status == CandidateStatus.DUPLICATE
