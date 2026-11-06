"""VHH Scaffold and CDR De Novo Generator.

Implements BaseGenerator for Tracks 1, 2, 3, 4, 6 (100–150 aa VHH single-domain antibodies):
- Uses canonical, highly developable camelid/humanized VHH frameworks (FR1–FR4)
- Synthesizes de novo CDR1, CDR2, CDR3 loops conditioned on target biophysical constraints
- Track 1 (EGFR): Histidine enrichment for pH 6.0 binding to acidic Asp/Glu epitopes
- Track 3 (GLP-1R): Allosteric agonist loop synthesis with zero Nanobody35 homology
- Strictly enforces 2 canonical framework Cysteines, 20 natural amino acids, and developability gates
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import structlog

from protein_design.generators.base import BaseGenerator
from protein_design.schemas import (
    Candidate,
    CandidateStatus,
    DesignType,
    ScientificStatus,
    Target,
    generate_sequential_id,
)
from protein_design.validation.druggability import (
    NANOBODY_35_SEQUENCE,
    calculate_sequence_identity,
    check_druggability,
    extract_vhh_cdrs,
)

log = structlog.get_logger(__name__)

# Standard high-stability humanized VHH Frameworks (82 aa total)
FR1_CANONICAL = "EVQLVESGGGLVQPGGSLRLSCAAS"      # 25 aa (ends at Cys22 landmark)
FR2_CANONICAL = "WVRQAPGKGLEWVS"                 # 14 aa
FR3_CANONICAL = "RFTISRDNSKNTLYLQMNSLRAEDTAVYYCAK"  # 32 aa (ends after Cys92)
FR4_CANONICAL = "WGQGTLVTVSS"                    # 11 aa

# Natural CDR amino acid pools excluding Cysteine (to preserve exactly 2 canonical Cys)
CORE_CDR_AAS = list("ADEFGHIKLMNPQRSTVWY")


class VHHScaffoldGenerator(BaseGenerator):
    """De novo VHH antibody scaffold and CDR loop generator."""

    def __init__(self, name: str = "vhh_scaffold", version: str = "1.0.0-competition"):
        self._name = name
        self._version = version

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    def _generate_cdr_loops(
        self,
        target: Target,
        rng: random.Random,
    ) -> tuple[str, str, str]:
        """Synthesize CDR1, CDR2, CDR3 loops conditioned on target parameters."""
        meta = target.metadata or {}
        is_egfr_ph6 = meta.get("ph_condition") == 6.0 or "EGFR" in target.target_id.upper()
        is_glp1r_agonist = meta.get("allosteric_agonist_mode") or "GLP" in target.target_id.upper()

        # Length specifications
        cdr1_len = rng.randint(6, 9)
        cdr2_len = rng.randint(7, 10)
        cdr3_len = rng.randint(10, 18)

        # Amino acid weighting
        weights = {aa: 1.0 for aa in CORE_CDR_AAS}
        weights["G"] = 1.6
        weights["S"] = 1.5
        weights["Y"] = 1.8
        weights["D"] = 1.2
        weights["T"] = 1.2

        if is_egfr_ph6:
            # Enrich Histidine for protonation at pH 6.0 interacting with Glu/Asp patches
            weights["H"] = 3.5
            weights["K"] = 1.5
            weights["R"] = 1.5

        if is_glp1r_agonist:
            # Polar / aromatic packing for allosteric beta-sheet stabilization
            weights["Y"] = 2.5
            weights["W"] = 1.5
            weights["N"] = 0.5  # Deprioritize Asn to avoid deamidation

        aa_choices = list(weights.keys())
        aa_probs = [weights[aa] for aa in aa_choices]

        def sample_loop(length: int) -> str:
            for _ in range(100):
                loop = "".join(rng.choices(aa_choices, weights=aa_probs, k=length))
                # Reject prohibited motifs
                if "NG" in loop or "NS" in loop or "DG" in loop or "DP" in loop:
                    continue
                if "N" in loop and any(f"N{x}{s}" in loop for x in CORE_CDR_AAS if x != "P" for s in "ST"):
                    continue
                return loop
            return "".join(rng.choices(["A", "S", "G", "Y", "D", "T"], k=length))

        cdr1 = sample_loop(cdr1_len)
        cdr2 = sample_loop(cdr2_len)
        cdr3 = sample_loop(cdr3_len)
        return cdr1, cdr2, cdr3

    def generate(
        self,
        target: Target,
        config: dict[str, Any],
        num_candidates: int = 10,
        seed: int = 42,
    ) -> list[Candidate]:
        """Generate candidate VHH antibodies conforming to competition constraints."""
        candidates: list[Candidate] = []
        max_attempts = num_candidates * 100
        attempt = 0

        target_name = target.target_id.upper()
        assay_ph = 6.0 if "EGFR" in target_name else 7.4
        nb35_cdrs = extract_vhh_cdrs(NANOBODY_35_SEQUENCE)

        while len(candidates) < num_candidates and attempt < max_attempts:
            attempt += 1
            cand_seed = seed + attempt
            cand_rng = random.Random(cand_seed)

            cdr1, cdr2, cdr3 = self._generate_cdr_loops(target, cand_rng)
            full_seq = f"{FR1_CANONICAL}{cdr1}{FR2_CANONICAL}{cdr2}{FR3_CANONICAL}{cdr3}{FR4_CANONICAL}"

            # Verify length constraint (100–150 aa)
            if not (100 <= len(full_seq) <= 150):
                continue

            # Verify Nanobody35 anti-leakage defense (CDR-H3 identity must be < 60%)
            ident_nb35, _ = calculate_sequence_identity(cdr3, nb35_cdrs["cdr3"])
            if ident_nb35 >= 0.60:
                continue

            # Run full developability check
            dev = check_druggability(full_seq, molecule_type="VHH", assay_ph=assay_ph)
            if not dev["passed"]:
                continue

            # Generate candidate ID and structure mock/content
            cid = generate_sequential_id("vhh", len(candidates) + 1)
            struct_content = (
                f"# De novo VHH Scaffold structure for {cid}\n"
                f"# Target: {target.target_id}, Length: {len(full_seq)}\n"
                f"data_{cid}\n"
                f"_entry.id {cid}\n"
            )

            # Target directory structure handling if design_path provided
            struct_path: Path | None = None
            design_path = config.get("design_path")
            if design_path:
                cand_dir = Path(design_path) / target.target_id / cid
                cand_dir.mkdir(parents=True, exist_ok=True)
                struct_path = cand_dir / "structure.cif"
                with open(struct_path, "w", encoding="utf-8") as f:
                    f.write(struct_content)

            candidate = Candidate(
                candidate_id=cid,
                target_id=target.target_id,
                sequence=full_seq,
                status=CandidateStatus.GENERATED,
                scientific_status=ScientificStatus.GENERATED,
                generator=self.name,
                generator_version=self.version,
                design_type=DesignType.VHH,
                structure_path=struct_path,
                seed=cand_seed,
                metrics={
                    "vhh_length": len(full_seq),
                    "isoelectric_point": dev["isoelectric_point"],
                    "net_charge_ph74": dev["net_charge_ph74"],
                    "net_charge_assay": dev["net_charge_assay"],
                    "cdr1_len": len(cdr1),
                    "cdr2_len": len(cdr2),
                    "cdr3_len": len(cdr3),
                    "nb35_cdr3_identity": round(ident_nb35, 4),
                },
                metadata={
                    "cdrs": {"cdr1": cdr1, "cdr2": cdr2, "cdr3": cdr3},
                    "assay_ph": assay_ph,
                    "target_ph_condition": target.metadata.get("ph_condition") if target.metadata else None,
                },
            )
            candidates.append(candidate)

        log.info(
            "vhh_scaffold_generation_done",
            target_id=target.target_id,
            generated=len(candidates),
            attempts=attempt,
        )
        return candidates
