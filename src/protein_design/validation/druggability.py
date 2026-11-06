"""Druggability, CDR De Novo Verification & Anti-Collision Engine.

Implements rules for Changjiang Cup 2026:
1. Unpaired Cysteines check (VHH strictly 2 canonical Cys; Minibinder 0 or even)
2. N-glycosylation motif detection: N-X-S/T (X != P)
3. Chemical liability motifs (deamidation: NG, NS; isomerization: DG, DP)
4. Multi-scheme VHH CDR extraction (IMGT, Kabat, Chothia, AbM)
5. Nanobody35 hard blacklist (PDB 6X18 entity 4 chain N) to block template leakage
6. Anti-collision across all 4 CDR numbering schemes simultaneously
7. Minibinder pairwise diversity check (< 85% pairwise identity)
8. Advanced developability gates: pI, net charge (pH 7.4 & assay pH), charge runs, hydrophobic patches
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from protein_design.core.exceptions import SecurityIntegrityError

# ---------------------------------------------------------------------------
# Nanobody35 (PDB 6X18 Entity 4 Chain N) - GLP-1R reference complex component
# ---------------------------------------------------------------------------
NANOBODY_35_SEQUENCE = (
    "QVQLQESGGGLVQPGGSLRLSCAASGFTFSNYKMNWVRQAPGKGLEWVSDISQSGASISYTGSVKG"
    "RFTISRDNAKNTLYLQMNSLKPEDTAVYYCARCPAPFTRDCFDVTSTTYAYRGQGTQVTVSS"
)


# ---------------------------------------------------------------------------
# Multi-Scheme CDR Extraction (IMGT, Kabat, Chothia, AbM)
# ---------------------------------------------------------------------------

def extract_vhh_cdrs_all_schemes(sequence: str) -> dict[str, dict[str, str]]:
    """Extract CDRs from a VHH sequence across all 4 major numbering schemes.

    Schemes:
    - IMGT:   CDR1: 27-38, CDR2: 56-65, CDR3: 105-117
    - Kabat:  CDR1: 31-35, CDR2: 50-65, CDR3: 95-102
    - Chothia: CDR1: 26-32, CDR2: 52-56, CDR3: 95-102
    - AbM:    CDR1: 26-35, CDR2: 50-58, CDR3: 95-102
    """
    seq = sequence.strip().upper()

    # Landmark anchor detection
    cys1_idx = seq.find("C")
    fr4_match = re.search(r"W[GQ][A-Z]G", seq[70:]) if len(seq) > 70 else None

    # Base coordinates
    cys1 = cys1_idx if cys1_idx != -1 else 22
    fr4_start = (70 + fr4_match.start()) if fr4_match else (len(seq) - 11)
    cys2 = seq[:fr4_start].rfind("C") if fr4_start > 0 else 92
    if cys2 == -1:
        cys2 = 92

    # Relative slice helpers (1-based relative to canonical numbering)
    # IMGT
    imgt_cdr1 = seq[cys1 + 4:cys1 + 16] if len(seq) > cys1 + 16 else ""
    imgt_cdr2 = seq[cys1 + 33:cys1 + 43] if len(seq) > cys1 + 43 else ""
    imgt_cdr3 = seq[cys2 + 1:fr4_start] if fr4_start > cys2 + 1 else ""

    # Kabat
    fr2_match = re.search(r"W[VFYI][RQ]", seq[cys1:70]) if len(seq) > 70 else None
    kabat_cdr1_end = (cys1 + fr2_match.start()) if fr2_match else (cys1 + 13)
    kabat_cdr1 = seq[max(0, kabat_cdr1_end - 5):kabat_cdr1_end]
    kabat_cdr2 = seq[kabat_cdr1_end + 14:cys2 - 32] if (cys2 - 32) > (kabat_cdr1_end + 14) else seq[49:65]
    kabat_cdr3 = seq[cys2 + 1:fr4_start] if fr4_start > cys2 + 1 else ""

    # Chothia
    chothia_cdr1 = seq[max(0, kabat_cdr1_end - 10):max(0, kabat_cdr1_end - 3)]
    chothia_cdr2 = seq[kabat_cdr1_end + 16:kabat_cdr1_end + 22] if len(seq) > (kabat_cdr1_end + 22) else ""
    chothia_cdr3 = kabat_cdr3

    # AbM (Martin)
    abm_cdr1 = seq[max(0, kabat_cdr1_end - 10):kabat_cdr1_end]
    abm_cdr2 = seq[kabat_cdr1_end + 14:kabat_cdr1_end + 23] if len(seq) > (kabat_cdr1_end + 23) else ""
    abm_cdr3 = kabat_cdr3

    return {
        "imgt": {"cdr1": imgt_cdr1, "cdr2": imgt_cdr2, "cdr3": imgt_cdr3},
        "kabat": {"cdr1": kabat_cdr1, "cdr2": kabat_cdr2, "cdr3": kabat_cdr3},
        "chothia": {"cdr1": chothia_cdr1, "cdr2": chothia_cdr2, "cdr3": chothia_cdr3},
        "abm": {"cdr1": abm_cdr1, "cdr2": abm_cdr2, "cdr3": abm_cdr3},
    }


def extract_vhh_cdrs(sequence: str, scheme: str = "kabat") -> dict[str, str]:
    """Extract CDR1, CDR2, and CDR3 regions for a single scheme (default: kabat)."""
    schemes = extract_vhh_cdrs_all_schemes(sequence)
    return schemes.get(scheme.lower(), schemes["kabat"])


NANOBODY_35_CDRS = extract_vhh_cdrs_all_schemes(NANOBODY_35_SEQUENCE)


# ---------------------------------------------------------------------------
# Biophysical Calculations: pI, Net Charge, Sequence Identity
# ---------------------------------------------------------------------------

def calculate_sequence_identity(seq1: str, seq2: str) -> tuple[float, float]:
    """Calculate sequence identity and coverage between two sequences.

    Returns:
        (identity, coverage) as floats in [0.0, 1.0].
    """
    s1, s2 = seq1.strip().upper(), seq2.strip().upper()
    if not s1 or not s2:
        return 0.0, 0.0

    min_len = min(len(s1), len(s2))
    max_len = max(len(s1), len(s2))

    matches = sum(1 for a, b in zip(s1, s2) if a == b)
    identity = matches / float(min_len)
    coverage = min_len / float(max_len)
    return identity, coverage


def calculate_net_charge(sequence: str, ph: float = 7.4) -> float:
    """Compute theoretical net charge via Henderson-Hasselbalch equation."""
    seq = sequence.strip().upper()
    pka = {
        "N_term": 9.6, "C_term": 2.34,
        "D": 3.86, "E": 4.25, "H": 6.0,
        "C": 8.33, "Y": 10.0, "K": 10.5, "R": 12.4,
    }
    # Positive charges
    charge = 1.0 / (1.0 + 10 ** (ph - pka["N_term"]))
    charge += seq.count("K") * (1.0 / (1.0 + 10 ** (ph - pka["K"])))
    charge += seq.count("R") * (1.0 / (1.0 + 10 ** (ph - pka["R"])))
    charge += seq.count("H") * (1.0 / (1.0 + 10 ** (ph - pka["H"])))

    # Negative charges
    charge -= 1.0 / (1.0 + 10 ** (pka["C_term"] - ph))
    charge -= seq.count("D") * (1.0 / (1.0 + 10 ** (pka["D"] - ph)))
    charge -= seq.count("E") * (1.0 / (1.0 + 10 ** (pka["E"] - ph)))
    charge -= seq.count("C") * (1.0 / (1.0 + 10 ** (pka["C"] - ph)))
    charge -= seq.count("Y") * (1.0 / (1.0 + 10 ** (pka["Y"] - ph)))
    return round(charge, 2)


def calculate_isoelectric_point(sequence: str) -> float:
    """Calculate theoretical isoelectric point (pI) using bisection root-finding."""
    seq = sequence.strip().upper()
    low, high = 2.0, 14.0
    for _ in range(50):
        mid = (low + high) / 2.0
        charge = calculate_net_charge(seq, mid)
        if charge > 0:
            low = mid
        else:
            high = mid
    return round((low + high) / 2.0, 2)


# ---------------------------------------------------------------------------
# Druggability & Manufacturability Checker (Audit Phase A Remediation)
# ---------------------------------------------------------------------------

def check_druggability(
    sequence: str,
    molecule_type: str = "minibinder",
    assay_ph: float = 7.4,
) -> dict[str, Any]:
    """Check sequence for druggability, developability, and chemical liabilities."""
    seq = sequence.strip().upper()
    mol_type = molecule_type.lower()
    liabilities: list[str] = []

    # 1. Cysteines check (VHH must have strictly 2 canonical Cysteines; Minibinder 0 or even)
    cys_count = seq.count("C")
    unpaired_cys = False

    if mol_type == "minibinder" and cys_count % 2 != 0:
        unpaired_cys = True
        liabilities.append(f"Minibinder has odd number of Cysteines ({cys_count})")
    elif mol_type in ("vhh", "nanobody") and cys_count != 2:
        unpaired_cys = True
        liabilities.append(
            f"VHH has non-canonical Cysteine count ({cys_count}, expected exactly 2 canonical Cys)"
        )

    # 2. N-glycosylation check (N-X-S/T where X != P)
    glyc_matches = [m.start() for m in re.finditer(r"N[^P][ST]", seq)]
    if glyc_matches:
        sites_str = ", ".join(f"pos {pos+1}" for pos in glyc_matches)
        liabilities.append(f"N-glycosylation motif N-X-S/T detected at {sites_str}")

    # 3. Chemical liabilities (deamidation: NG, NS; isomerization: DG, DP)
    ng_matches = [m.start() for m in re.finditer(r"N[GS]", seq)]
    dg_matches = [m.start() for m in re.finditer(r"D[GP]", seq)]

    if mol_type in ("vhh", "nanobody"):
        cdrs = extract_vhh_cdrs(seq)
        for cdr_name, cdr_seq in cdrs.items():
            if re.search(r"N[GS]", cdr_seq):
                liabilities.append(f"Deamidation motif (NG/NS) found in {cdr_name.upper()}")
            if re.search(r"D[GP]", cdr_seq):
                liabilities.append(f"Isomerization motif (DG/DP) found in {cdr_name.upper()}")
    else:
        if ng_matches:
            liabilities.append(f"Deamidation motif (NG/NS) detected at positions {ng_matches}")
        if dg_matches:
            liabilities.append(f"Isomerization motif (DG/DP) detected at positions {dg_matches}")

    # 4. Isoelectric Point (pI) & Net Charge Gates (Audit Item 8)
    pi = calculate_isoelectric_point(seq)
    charge_74 = calculate_net_charge(seq, ph=7.4)
    charge_assay = calculate_net_charge(seq, ph=assay_ph)

    pi_range = (5.0, 9.0) if mol_type in ("vhh", "nanobody") else (4.5, 8.5)
    if not (pi_range[0] <= pi <= pi_range[1]):
        liabilities.append(
            f"Isoelectric point (pI={pi}) outside optimal range {pi_range[0]}-{pi_range[1]}"
        )

    if not (-5.0 <= charge_74 <= 5.0):
        liabilities.append(
            f"Net charge at physiological pH 7.4 ({charge_74:+.1f}) exceeds expression gate [-5.0, +5.0]"
        )

    if not (-3.0 <= charge_assay <= 3.0):
        liabilities.append(
            f"Net charge at assay pH {assay_ph} ({charge_assay:+.1f}) exceeds assay gate [-3.0, +3.0]"
        )

    # 5. Charge Runs: No contiguous >= 4 same-charge residues (KKKK, DDDD, EEEE, RRRR)
    charge_runs = re.findall(r"[KR]{4,}|[DE]{4,}", seq)
    if charge_runs:
        liabilities.append(f"Repulsive charge run detected: {charge_runs}")

    # 6. Hydrophobic Patches: No contiguous >= 5 large hydrophobic residues (L/I/V/F/W/Y)
    hydrophobic_patches = re.findall(r"[LIVFWY]{5,}", seq)
    if hydrophobic_patches:
        liabilities.append(f"Aggregation-prone hydrophobic patch detected: {hydrophobic_patches}")

    # 7. N-terminal Pyroglutamate check (If Q -> liabilities flag for Q->E mutation)
    if seq.startswith("Q"):
        liabilities.append("N-terminal Gln (Q) prone to pyroglutamate cyclization; recommend E")

    passed = len(liabilities) == 0
    return {
        "passed": passed,
        "isoelectric_point": pi,
        "net_charge_ph74": charge_74,
        "net_charge_assay": charge_assay,
        "cysteine_count": cys_count,
        "unpaired_cysteines": unpaired_cys,
        "glycosylation_sites": len(glyc_matches),
        "deamidation_motifs": len(ng_matches),
        "isomerization_motifs": len(dg_matches),
        "charge_runs": charge_runs,
        "hydrophobic_patches": hydrophobic_patches,
        "liabilities": liabilities,
    }


# ---------------------------------------------------------------------------
# Anti-Collision Verification (All 4 Schemes + Nanobody35 Blacklist)
# ---------------------------------------------------------------------------

def verify_anti_collision(
    candidate_seq: str,
    pool_sequences: Sequence[str],
    molecule_type: str = "minibinder",
    candidate_id: str = "",
) -> None:
    """Verify anti-collision against a candidate pool and reference blacklists."""
    cand_seq = candidate_seq.strip().upper()
    mol_type = molecule_type.lower()

    if mol_type in ("vhh", "nanobody"):
        cand_schemes = extract_vhh_cdrs_all_schemes(cand_seq)

        # 1. Hard Blacklist check against Nanobody35 (PDB 6X18 Entity 4 Chain N)
        for scheme_name, cand_cdrs in cand_schemes.items():
            nb35_cdr3 = NANOBODY_35_CDRS[scheme_name]["cdr3"]
            ident, _cov = calculate_sequence_identity(cand_cdrs["cdr3"], nb35_cdr3)
            if ident >= 0.70:
                raise SecurityIntegrityError(
                    f"Disqualification Risk: Candidate {candidate_id} has {ident:.1%} CDR-H3 "
                    f"identity to Nanobody35 under {scheme_name.upper()} scheme. Hard rejected."
                )

        # 2. Check candidate pool across ALL 4 CDR schemes simultaneously
        for idx, other_seq in enumerate(pool_sequences):
            if not other_seq:
                continue
            other_schemes = extract_vhh_cdrs_all_schemes(other_seq)
            for scheme_name in ("imgt", "kabat", "chothia", "abm"):
                c_cdrs = cand_schemes[scheme_name]
                o_cdrs = other_schemes[scheme_name]
                matches = 0
                for loop in ("cdr1", "cdr2", "cdr3"):
                    ident, cov = calculate_sequence_identity(c_cdrs[loop], o_cdrs[loop])
                    if ident == 1.0 and cov >= 0.90:
                        matches += 1
                if matches == 3:
                    raise SecurityIntegrityError(
                        f"Anti-collision violation for {candidate_id}: Identical CDRs "
                        f"(>90% cov, 100% id) under {scheme_name.upper()} scheme with index {idx}."
                    )
    else:
        # Minibinder pairwise diversity check (< 85% sequence identity)
        for idx, other_seq in enumerate(pool_sequences):
            if not other_seq:
                continue
            ident, _cov = calculate_sequence_identity(cand_seq, other_seq)
            if ident >= 0.85:
                raise SecurityIntegrityError(
                    f"Anti-collision violation for {candidate_id}: Sequence identity ({ident:.1%}) "
                    f"exceeds 85% diversity ceiling with candidate at index {idx}."
                )
