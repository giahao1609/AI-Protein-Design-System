"""Druggability, CDR De Novo Verification & Anti-Collision Engine.

Implements rules for Changjiang Cup 2026:
1. Unpaired Cysteines check
2. N-glycosylation motif detection: N-X-S/T (X != P)
3. Chemical liability motifs (deamidation: NG, NS; isomerization: DG)
4. VHH CDR extraction (CDR1, CDR2, CDR3)
5. Anti-collision & sequence identity checks (coverage > 90%, identity = 100% for CDRs)
6. Minibinder pairwise diversity check (< 85% pairwise identity)
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from protein_design.core.exceptions import SecurityIntegrityError


def extract_vhh_cdrs(sequence: str) -> dict[str, str]:
    """Extract CDR1, CDR2, and CDR3 regions from a VHH antibody sequence.

    Uses canonical conserved VHH sequence landmarks:
    - FR1 ends after first canonical Cys (~Cys23). CDR1 runs until conserved W-X-R motif.
    - CDR2 is located between FR2 (W-X-R-Q) and FR3 (R-F/Y-T-I-S).
    - CDR3 is located between conserved 2nd Cys in FR3 and conserved W-G-X-G motif in FR4.
    """
    seq = sequence.strip().upper()
    cdrs: dict[str, str] = {"cdr1": "", "cdr2": "", "cdr3": ""}

    # 1. Locate 1st canonical Cysteine
    cys1_idx = seq.find("C")
    # Locate FR4 landmark 'WG' or 'W[G|A|Q]QG' near C-terminus
    fr4_match = re.search(r"W[GQ][A-Z]G", seq[70:])

    if cys1_idx != -1 and fr4_match:
        fr4_start = 70 + fr4_match.start()

        # Locate 2nd canonical Cysteine before FR4
        cys2_idx = seq[:fr4_start].rfind("C")

        # CDR3 is region between 2nd Cys and FR4 start
        if cys2_idx != -1 and (fr4_start - cys2_idx) >= 3:
            cdrs["cdr3"] = seq[cys2_idx + 1:fr4_start]

        # Locate FR2 landmark (conserved W[VFYI][RQ])
        fr2_match = re.search(r"W[VFYI][RQ]", seq[cys1_idx:70])
        if fr2_match:
            cdr1_end = cys1_idx + fr2_match.start()
            cdr1_start = cys1_idx + 1
            if cdr1_end > cdr1_start:
                cdrs["cdr1"] = seq[cdr1_start:cdr1_end]

            # FR3 start landmark (R[FYL][TS][IS])
            fr3_search_end = cys2_idx if cys2_idx != -1 else 95
            fr3_match = re.search(r"R[FYL][TS][IS]", seq[cdr1_end:fr3_search_end])
            if fr3_match:
                cdr2_start = cdr1_end + 14  # Typical FR2 length is ~14 aa
                cdr2_end = cdr1_end + fr3_match.start()
                if cdr2_end > cdr2_start:
                    cdrs["cdr2"] = seq[cdr2_start:cdr2_end]

    # Fallback to standard relative positional heuristic if motif anchors were unusual
    if not cdrs["cdr3"]:
        cdrs["cdr1"] = seq[25:35] if len(seq) > 35 else ""
        cdrs["cdr2"] = seq[49:65] if len(seq) > 65 else ""
        cdrs["cdr3"] = seq[95:len(seq)-11] if len(seq) > 106 else seq[95:]

    return cdrs


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


def check_druggability(
    sequence: str,
    molecule_type: str = "minibinder",
) -> dict[str, Any]:
    """Check sequence for druggability liabilities (Cysteines, Glycosylation, Degradation).

    Returns:
        dict containing 'passed', 'cysteine_count', 'unpaired_cysteines', 'glycosylation_sites',
        'deamidation_motifs', 'isomerization_motifs', and 'liabilities'.
    """
    seq = sequence.strip().upper()
    liabilities: list[str] = []

    # 1. Cysteines check
    cys_count = seq.count("C")
    mol_type = molecule_type.lower()
    unpaired_cys = False

    if mol_type == "minibinder" and cys_count % 2 != 0:
        # Minibinders should ideally have 0 cysteines or even pairs (disulfides)
        unpaired_cys = True
        liabilities.append(f"Minibinder has odd number of Cysteines ({cys_count})")
    elif mol_type in ("vhh", "nanobody") and cys_count not in (2, 4):
        # VHH has 2 canonical cysteines; extra cysteines must be paired (total 2 or 4)
        unpaired_cys = True
        liabilities.append(
            f"VHH has non-standard Cysteine count ({cys_count}, expected 2 or 4)"
        )

    # 2. N-glycosylation check (N-X-S/T where X != P)
    glyc_matches = [m.start() for m in re.finditer(r"N[^P][ST]", seq)]
    if glyc_matches:
        sites_str = ", ".join(f"pos {pos+1}" for pos in glyc_matches)
        liabilities.append(f"N-glycosylation motif N-X-S/T detected at {sites_str}")

    # 3. Chemical liabilities (deamidation: NG, NS; isomerization: DG)
    ng_matches = [m.start() for m in re.finditer(r"N[GS]", seq)]
    dg_matches = [m.start() for m in re.finditer(r"DG", seq)]

    # Check if they occur in CDRs for VHH
    if mol_type in ("vhh", "nanobody"):
        cdrs = extract_vhh_cdrs(seq)
        for cdr_name, cdr_seq in cdrs.items():
            if re.search(r"N[GS]", cdr_seq):
                liabilities.append(f"Deamidation motif (NG/NS) found in {cdr_name.upper()}")
            if "DG" in cdr_seq:
                liabilities.append(f"Isomerization motif (DG) found in {cdr_name.upper()}")
    else:
        if ng_matches:
            liabilities.append(f"Deamidation motif (NG/NS) detected at positions {ng_matches}")
        if dg_matches:
            liabilities.append(f"Isomerization motif (DG) detected at positions {dg_matches}")

    passed = len(liabilities) == 0
    return {
        "passed": passed,
        "cysteine_count": cys_count,
        "unpaired_cysteines": unpaired_cys,
        "glycosylation_sites": len(glyc_matches),
        "deamidation_motifs": len(ng_matches),
        "isomerization_motifs": len(dg_matches),
        "liabilities": liabilities,
    }


def verify_anti_collision(
    candidate_seq: str,
    pool_sequences: Sequence[str],
    molecule_type: str = "minibinder",
    candidate_id: str = "",
) -> None:
    """Verify anti-collision against a candidate pool.

    - For VHH: CDR identity == 100% and coverage > 90% is blocked.
    - For Minibinder: Pairwise sequence identity >= 85% is blocked.
    """
    cand_seq = candidate_seq.strip().upper()
    mol_type = molecule_type.lower()

    if mol_type in ("vhh", "nanobody"):
        cand_cdrs = extract_vhh_cdrs(cand_seq)
        for idx, other_seq in enumerate(pool_sequences):
            if not other_seq:
                continue
            other_cdrs = extract_vhh_cdrs(other_seq)
            # Compare CDR1, CDR2, CDR3 combined or CDR3
            cdr_matches = 0
            for k in ("cdr1", "cdr2", "cdr3"):
                ident, cov = calculate_sequence_identity(cand_cdrs[k], other_cdrs[k])
                if ident == 1.0 and cov >= 0.90:
                    cdr_matches += 1
            if cdr_matches == 3:
                raise SecurityIntegrityError(
                    f"Anti-collision violation for {candidate_id}: Identical CDRs "
                    f"(>90% cov, 100% id) with candidate at index {idx}."
                )
    else:
        # Minibinder pairwise diversity
        for idx, other_seq in enumerate(pool_sequences):
            if not other_seq:
                continue
            ident, _cov = calculate_sequence_identity(cand_seq, other_seq)
            if ident >= 0.85:
                raise SecurityIntegrityError(
                    f"Anti-collision violation for {candidate_id}: Sequence identity ({ident:.1%}) "
                    f"exceeds 85% diversity ceiling with candidate at index {idx}."
                )
