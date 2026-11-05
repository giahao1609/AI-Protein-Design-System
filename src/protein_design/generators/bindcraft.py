"""BindCraft Generator Adapter.

Implements the BaseGenerator interface for BindCraft, an automated pipeline
for de novo protein binder design (Nature 646, 483-492 (2025)).

Adheres strictly to the frozen Base V1 contract, upstream BindCraft JSON
settings schema, exact CSV output headers, and mmCIF structural conversion.
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import structlog

from protein_design.core.exceptions import ConfigError, GenerationError
from protein_design.generators.base import BaseGenerator
from protein_design.schemas import (
    Candidate,
    CandidateStatus,
    DesignType,
    ScientificStatus,
    Target,
    generate_sequential_id,
    hash_string,
)

log = structlog.get_logger(__name__)


def serialize_target_settings(
    target: Target,
    config: dict[str, Any],
    output_dir: Path,
    num_candidates: int = 10,
) -> dict[str, Any]:
    """Serialize target parameters into authentic upstream BindCraft JSON settings.

    Upstream verified schema requires exactly 7 canonical keys:
    - starting_pdb: Path to target PDB file
    - chains: Target chain identifier(s)
    - target_hotspot_residues: Comma-separated target hotspot residue string
    - lengths: List of binder lengths to design
    - number_of_final_designs: Target number of accepted binders
    - binder_name: Base label for generated designs
    - design_path: Output directory path
    """
    params = config.get("params", {}) if isinstance(config.get("params"), dict) else {}

    starting_pdb = (
        params.get("starting_pdb")
        or config.get("starting_pdb")
        or (str(target.structure_file) if target.structure_file else "")
    )
    if not starting_pdb:
        starting_pdb = "/workspace/target.pdb"

    # Target chains
    chains = params.get("chains") or config.get("chains")
    if not chains:
        if target.chains:
            chains = ",".join(c.chain_id for c in target.chains)
        else:
            chains = "A"

    # Hotspot residues
    hotspots = params.get("target_hotspot_residues") or config.get("target_hotspot_residues")
    if not hotspots:
        if target.hotspots:
            hotspots = ",".join(f"{h.chain_id}{h.residue}" for h in target.hotspots)
        else:
            hotspots = ""

    # Binder lengths
    lengths = (
        params.get("lengths")
        or config.get("lengths")
        or params.get("binder_lengths")
        or config.get("binder_lengths")
    )
    if not lengths:
        min_l = params.get("min_length", config.get("min_length", 50))
        max_l = params.get("max_length", config.get("max_length", 70))
        lengths = [int(min_l), int(max_l)] if min_l != max_l else [int(min_l)]
    elif isinstance(lengths, (int, float)):
        lengths = [int(lengths)]
    else:
        lengths = [int(x) for x in lengths]

    binder_name = (
        params.get("binder_name")
        or config.get("binder_name")
        or f"{target.target_id}_binder"
    )

    settings = {
        "design_path": str(output_dir),
        "binder_name": str(binder_name),
        "starting_pdb": str(starting_pdb),
        "chains": str(chains),
        "target_hotspot_residues": str(hotspots),
        "lengths": lengths,
        "number_of_final_designs": int(num_candidates),
    }
    return settings


def convert_pdb_to_mmcif(
    pdb_path: Path, output_cif_path: Path, chain_id: str | None = None
) -> Path:
    """Convert a PDB file to mmCIF format using gemmi.

    If chain_id is provided, only that chain is written (e.g. for binder-only structure).
    """
    import gemmi

    output_cif_path.parent.mkdir(parents=True, exist_ok=True)
    structure = gemmi.read_structure(str(pdb_path))

    if chain_id:
        structure_copy = structure.clone()
        for model in structure_copy:
            chains_to_remove = [c.name for c in model if c.name != chain_id]
            for c_name in chains_to_remove:
                model.remove_chain(c_name)
        doc = structure_copy.make_mmcif_document()
    else:
        doc = structure.make_mmcif_document()

    doc.write_file(str(output_cif_path))
    return output_cif_path


def parse_bindcraft_output(
    output_dir: Path,
    target_id: str,
    candidate_store_dir: Path | None = None,
    generator_name: str = "bindcraft",
    generator_version: str = "0.1.0-draft",
) -> tuple[list[Candidate], dict[str, Any]]:
    """Parse BindCraft outputs from output directory.

    Extracts sequences strictly from native column 'Sequence' in final_design_stats.csv.
    Converts PDB coordinates to mmCIF using gemmi.
    Extracts all biophysical and model metrics with accurate units and scales.
    Ingests failure rejection stats from failure_csv.csv.
    """
    # Look for final_design_stats.csv
    csv_path = output_dir / "final_design_stats.csv"
    if not csv_path.exists():
        csv_path = output_dir / "Accepted" / "final_design_stats.csv"

    if not csv_path.exists():
        raise GenerationError(f"Missing BindCraft score CSV: {csv_path}")

    # Parse failure counters if available
    rejection_counts: dict[str, int] = {}
    failure_csv = output_dir / "failure_csv.csv"
    if failure_csv.exists():
        try:
            with open(failure_csv, mode="r", encoding="utf-8") as f:
                fail_reader = csv.reader(f)
                next(fail_reader, None)
                for r_row in fail_reader:
                    if len(r_row) >= 2:
                        try:
                            rejection_counts[r_row[0].strip()] = int(r_row[1].strip())
                        except ValueError:
                            pass
        except Exception as e:
            log.warning("bindcraft_failure_csv_parse_error", error=str(e))

    candidates: list[Candidate] = []
    seen_hashes: set[str] = set()

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "Sequence" not in reader.fieldnames:
            raise GenerationError(
                f"Invalid BindCraft CSV schema: missing canonical 'Sequence' column in {csv_path}"
            )

        for idx, row in enumerate(reader):
            design_name = row.get("Design", f"design_{idx+1}")
            sequence = row.get("Sequence", "").strip()
            if not sequence:
                continue

            seq_hash = hash_string(sequence)
            status = CandidateStatus.GENERATED
            if seq_hash in seen_hashes:
                status = CandidateStatus.DUPLICATE
            seen_hashes.add(seq_hash)

            # Extract seed
            seed_val: int | None = None
            if row.get("Seed"):
                try:
                    seed_val = int(float(row["Seed"]))
                except ValueError:
                    seed_val = None

            # Parse numeric metrics safely
            def _parse_float(key: str) -> float | None:
                val = row.get(key)
                if val is not None and val != "":
                    try:
                        return float(val)
                    except ValueError:
                        raise GenerationError(
                            f"Corrupted numeric metric '{key}' with value '{val}'"
                        )
                return None

            def _parse_int(key: str) -> int | None:
                val = row.get(key)
                if val is not None and val != "":
                    try:
                        return int(float(val))
                    except ValueError:
                        raise GenerationError(
                            f"Corrupted integer metric '{key}' with value '{val}'"
                        )
                return None

            raw_plddt = _parse_float("Average_pLDDT")
            metrics: dict[str, Any] = {}
            if raw_plddt is not None:
                metrics["raw_af2_plddt"] = raw_plddt
                metrics["af2_plddt"] = round(raw_plddt * 100.0, 4)

            metrics["af2_ptm"] = _parse_float("Average_pTM")
            metrics["af2_iptm"] = _parse_float("Average_i_pTM")
            metrics["af2_pae"] = _parse_float("Average_pAE")
            metrics["af2_interface_pae"] = _parse_float("Average_i_pAE")
            metrics["af2_interface_plddt"] = _parse_float("Average_i_pLDDT")
            metrics["af2_ss_plddt"] = _parse_float("Average_ss_pLDDT")

            metrics["unrelaxed_clashes"] = _parse_int("Average_Unrelaxed_Clashes")
            metrics["relaxed_clashes"] = _parse_int("Average_Relaxed_Clashes")

            metrics["binder_energy_score"] = _parse_float("Average_Binder_Energy_Score")
            metrics["surface_hydrophobicity"] = _parse_float("Average_Surface_Hydrophobicity")
            metrics["pyrosetta_interface_sc"] = _parse_float("Average_ShapeComplementarity")
            metrics["pyrosetta_interface_packstat"] = _parse_float("Average_PackStat")
            metrics["pyrosetta_interface_dg"] = _parse_float("Average_dG")
            metrics["pyrosetta_interface_dsasa"] = _parse_float("Average_dSASA")
            metrics["pyrosetta_dg_dsasa"] = _parse_float("Average_dG/dSASA")
            metrics["interface_sasa_pct"] = _parse_float("Average_Interface_SASA_%")

            metrics["hotspot_rmsd"] = _parse_float("Average_Hotspot_RMSD")
            metrics["target_rmsd"] = _parse_float("Average_Target_RMSD")
            metrics["binder_rmsd"] = _parse_float("Average_Binder_RMSD")

            # Remove None values
            metrics = {k: v for k, v in metrics.items() if v is not None}

            # Model metrics (1..5)
            model_metrics: dict[str, dict[str, float]] = {}
            for m in range(1, 6):
                m_dict: dict[str, float] = {}
                for metric_label in ["pLDDT", "pTM", "i_pTM", "pAE", "i_pAE"]:
                    col = f"{m}_{metric_label}"
                    if row.get(col):
                        try:
                            m_dict[metric_label] = float(row[col])
                        except ValueError:
                            pass
                if m_dict:
                    model_metrics[str(m)] = m_dict

            candidate_id = generate_sequential_id("cand", idx + 1)

            # Locate PDB file
            pdb_cand_file = output_dir / "Accepted" / f"{design_name}.pdb"
            if not pdb_cand_file.exists():
                pdb_cand_file = output_dir / "Accepted" / "Ranked" / f"{design_name}.pdb"
            if not pdb_cand_file.exists():
                pdb_cand_file = output_dir / f"{design_name}.pdb"

            binder_cif_path: Path | None = None
            complex_cif_path: Path | None = None

            if pdb_cand_file.exists():
                if candidate_store_dir:
                    c_dir = candidate_store_dir / target_id / candidate_id
                    c_dir.mkdir(parents=True, exist_ok=True)
                    binder_cif_path = c_dir / "binder.cif"
                    complex_cif_path = c_dir / "complex.cif"
                else:
                    binder_cif_path = output_dir / "Accepted" / f"{design_name}_binder.cif"
                    complex_cif_path = output_dir / "Accepted" / f"{design_name}_complex.cif"

                # Convert PDB to mmCIF via Gemmi
                try:
                    convert_pdb_to_mmcif(pdb_cand_file, complex_cif_path)
                    convert_pdb_to_mmcif(pdb_cand_file, binder_cif_path, chain_id="B")
                except Exception as conv_err:
                    log.warning("mmcif_conversion_error", design=design_name, error=str(conv_err))
            else:
                log.warning("bindcraft_pdb_missing", design=design_name, path=str(pdb_cand_file))

            candidate = Candidate(
                candidate_id=candidate_id,
                target_id=target_id,
                sequence=sequence,
                design_type=DesignType.MINIBINDER,
                generator=generator_name,
                generator_version=generator_version,
                seed=seed_val,
                status=status,
                scientific_status=ScientificStatus.GENERATED,
                structure_path=binder_cif_path,
                complex_structure_path=complex_cif_path,
                metrics=metrics,
                metadata={
                    "design_name": design_name,
                    "model_metrics": model_metrics,
                    "bindcraft_raw_metrics": {
                        k: v for k, v in row.items() if k not in ("Design", "Sequence")
                    },
                },
            )
            candidates.append(candidate)

    summary = {
        "total_parsed": len(candidates),
        "rejection_counts": rejection_counts,
    }
    return candidates, summary


class BindCraftGenerator(BaseGenerator):
    """BindCraft protein binder generator adapter.

    Executes either a local Docker container or MockRunner for test isolation.
    Conforms to the frozen BaseGenerator abstract interface.
    """

    def __init__(
        self,
        runner_type: str = "mock",
        docker_image: str = "bindcraft:latest",
        timeout_seconds: int = 1800,
        mock_output_dir: Path | None = None,
    ):
        self.runner_type = runner_type
        self.docker_image = docker_image
        self.timeout_seconds = timeout_seconds
        self.mock_output_dir = mock_output_dir

    @property
    def name(self) -> str:
        return "bindcraft"

    @property
    def version(self) -> str:
        return "0.1.0-draft"

    def validate_config(self, config: dict[str, Any]) -> None:
        """Validate generator configuration."""
        params = config.get("params", {}) if isinstance(config.get("params"), dict) else {}
        if "binder_lengths" in params and not isinstance(params["binder_lengths"], (list, int)):
            raise ConfigError("Invalid binder_lengths: must be an int or list of ints")

    def generate(
        self,
        target: Target,
        config: dict[str, Any],
        num_candidates: int = 10,
        seed: int = 42,
    ) -> list[Candidate]:
        """Generate protein binders using BindCraft."""
        self.validate_config(config)

        params = config.get("params", {}) if isinstance(config.get("params"), dict) else {}
        if params.get("fail_generation", config.get("fail_generation", False)):
            raise GenerationError("Simulated BindCraft generator crash", candidate_id=None)

        runner = params.get("runner_type") or config.get("runner_type") or self.runner_type
        output_dir_str = params.get("output_dir") or config.get("output_dir")
        output_dir = Path(output_dir_str) if output_dir_str else Path("data/bindcraft_run")
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Serialize target settings JSON
        target_settings = serialize_target_settings(
            target=target,
            config=config,
            output_dir=output_dir,
            num_candidates=num_candidates,
        )
        settings_file = output_dir / "target_settings.json"
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(target_settings, f, indent=2)

        # 2. Execute runner
        if runner == "mock":
            self._execute_mock(output_dir)
        elif runner == "docker":
            self._execute_docker(output_dir, settings_file)
        else:
            raise ConfigError(f"Unsupported runner_type: {runner}")

        # 3. Parse output directory
        candidate_store = params.get("candidate_store_dir") or config.get("candidate_store_dir")
        candidates, _ = parse_bindcraft_output(
            output_dir=output_dir,
            target_id=target.target_id,
            candidate_store_dir=Path(candidate_store) if candidate_store else None,
            generator_name=self.name,
            generator_version=self.version,
        )

        return candidates[:num_candidates]

    def _execute_mock(self, output_dir: Path) -> None:
        """Inject mock fixtures into the output directory if needed."""
        mock_src = self.mock_output_dir or Path("tests/fixtures/bindcraft_output")
        if not mock_src.exists():
            raise GenerationError(f"Mock output fixtures not found at {mock_src}")

        # Copy fixtures to output_dir if output_dir is different
        if mock_src.resolve() != output_dir.resolve():
            for item in mock_src.iterdir():
                dest = output_dir / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)

    def _execute_docker(self, output_dir: Path, settings_file: Path) -> None:
        """Execute BindCraft inside Docker with timeout and supervisor isolation."""
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{output_dir.resolve()}:/workspace",
            "-w", "/workspace",
            self.docker_image,
            "python", "-u", "/bindcraft/bindcraft.py",
            "--settings", f"/workspace/{settings_file.name}",
        ]

        log.info("bindcraft_docker_launch", cmd=cmd)
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError as err:
            raise GenerationError(f"Docker executable not found: {err}")

        # Execution supervisor with timeout
        start_time = time.time()
        while True:
            retcode = process.poll()
            if retcode is not None:
                break
            if time.time() - start_time > self.timeout_seconds:
                log.warning("bindcraft_timeout_terminating", pid=process.pid)
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    log.error("bindcraft_escalating_to_sigkill", pid=process.pid)
                    process.kill()
                raise GenerationError(
                    f"BindCraft container exceeded timeout of {self.timeout_seconds} seconds"
                )
            time.sleep(1)

        _stdout, stderr = process.communicate()
        if retcode != 0:
            raise GenerationError(
                f"BindCraft execution failed with exit code {retcode}: {stderr}"
            )

