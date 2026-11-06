# CHANGJIANG CUP 2026 OFFICIAL RULES RECONCILIATION V2
## Comprehensive Evidence-Based Audit & Bilingual Specification Conflict Analysis

**Project:** AI Protein Design System  
**Campaign Branch:** `feature/changjiang-cup-2026`  
**Reference Cloud Execution:** AsterFire Execution 24000 (Plan 22425, Cluster `SAI-compute-NEW`)  
**Audit Timestamp:** 2026-11-06T15:40:00+07:00  
**Lead Auditor:** Houhou (Front Agent & Tech Lead, MyAgent)  
**Status:** Verification Complete — CONDITIONAL GO with Target Conflict Mitigation  

---

## 1. Executive Summary

This audit establishes an exhaustive reconciliation between the AI Protein Design System implementation and the official specifications published for the **Changjiang Cup - Global AI Protein Design Challenge 2026** (organized by Shanghai Jiao Tong University, Shanghai AI Laboratory, Lin-gang Laboratory, Changping Laboratory, and partner institutions; hosted on `https://aiprotein.sjtu.edu.cn/`).

### Critical Finding: Bilingual Specification Discrepancy
An official discrepancy has been identified between the Chinese-language announcements and the English-language portal pages regarding the residue definitions of three key targets:
1. **Target 3 (GLP-1R):** Chinese text defines the target as **Ala21–Glu139** (119 aa, soluble Extracellular Domain only), whereas the English portal lists **Arg24–Ser432** (409 aa, full Extracellular Domain plus the entire 7-Transmembrane Helix core).
2. **Target 6 (TNFR1):** Chinese text defines **Met1–Thr211** (211 aa, full precursor including the 29-aa hydrophobic signal peptide), whereas the English portal lists **Leu30–Thr211** (182 aa, mature cleaved ectodomain).
3. **Target 7 (IL-7Rα):** Chinese text defines **Met1–Gly236** (236 aa, full precursor including the 20-aa hydrophobic signal peptide), whereas the English portal lists **Glu21–Asp239** (219 aa, mature cleaved ectodomain extending to Asp239).

### Governance Policy
In accordance with engineering safety and scientific integrity guidelines:
- Neither version is assumed to be an official rule change without formal organizer confirmation.
- Disputed ranges are classified as `PENDING_ORGANIZER_CONFIRMATION`.
- Existing candidate sequences, target FASTA files, and completed AsterFire Execution 24000 artifacts are preserved intact without speculative overwrite.
- A dual-mode contingency plan and a formal Chinese-language inquiry message for the organizing committee have been prepared.

---

## 2. Official Source Comparison

The audit cross-referenced official and partner channels accessed on 2026-11-06:

| Source Identifier | Exact URL | Language | Key Relevant Excerpt |
|---|---|---|---|
| **SJTU Portal (Main)** | `https://aiprotein.sjtu.edu.cn/` | Bilingual | General challenge overview, institutional hosts (SJTU, Shanghai AI Lab, Lin-gang Lab). |
| **SJTU Chinese Portal** | `https://aiprotein.sjtu.edu.cn/?lang=zh` | Chinese | Published target list with coordinates: GLP-1R (Ala21-Glu139), TNFR1 (Met1-Thr211), IL-7Ra (Met1-Gly236). |
| **SJTU English Portal** | `https://aiprotein.sjtu.edu.cn/?lang=en` | English | Translated target list with coordinates: GLP-1R (Arg24-Ser432), TNFR1 (Leu30-Thr211), IL-7Ra (Glu21-Asp239). |
| **SJTU Targets Page** | `https://aiprotein.sjtu.edu.cn/targets` | Bilingual | Specification of molecule types (Tracks 1, 3, 4, 6: VHH 100–150 aa; Tracks 2, 5, 7: Minibinder 40–100 aa). |
| **SJTU Rules Page** | `https://aiprotein.sjtu.edu.cn/rules` | Bilingual | Evaluation protocol: ESMFold2, ipSAE, 1 seed, 1 sample, no templates, Target MSA only, Binder no MSA. Max 20 candidates per track. |
| **Sidereus AI Announcement** | `https://sidereus-ai.com/news/29` | Chinese | Partner compute announcement: AsterFire platform and SPONGE Mokda computational workbench support. |

---

## 3. Full Seven-Target Specification Matrix

The table below summarizes the audited specifications across all seven official tracks:

| Track | Target Identifier | Molecule Type | Length Constraint | Chinese / Announcement Range | English Portal Range | Status in System |
|---|---|---|---|---|---|---|
| **1** | **EGFR** | VHH (Nanobody) | 100–150 aa | Met1–Ser645 (Signal masked: 1–24) | Leu25–Ser645 | **CONFIRMED / CONSISTENT** (Signal peptide masked in local pipeline) |
| **2** | **TNF-α** | Minibinder | 40–100 aa | Val77–Leu233 (157 aa mature monomer) | Val77–Leu233 | **CONFIRMED / CONSISTENT** (Homotrimer biological context) |
| **3** | **GLP-1R** | VHH (Nanobody) | 100–150 aa | **Ala21–Glu139** (119 aa, ECD only) | **Arg24–Ser432** (409 aa, ECD + 7TM) | **PENDING_ORGANIZER_CONFIRMATION** (Severe architectural conflict) |
| **4** | **TfR1** | VHH (Nanobody) | 100–150 aa | Cys89–Phe760 (672 aa ectodomain) | Cys89–Phe760 | **CONFIRMED / CONSISTENT** (Homodimer biological context) |
| **5** | **TL1A** | Minibinder | 40–100 aa | Leu72–Leu251 (180 aa mature monomer) | Leu72–Leu251 | **CONFIRMED / CONSISTENT** (Homotrimer biological context) |
| **6** | **TNFR1** | VHH (Nanobody) | 100–150 aa | **Met1–Thr211** (211 aa, with signal) | **Leu30–Thr211** (182 aa, mature ECD) | **PENDING_ORGANIZER_CONFIRMATION** (Signal peptide cleavage boundary) |
| **7** | **IL-7Rα** | Minibinder | 40–100 aa | **Met1–Gly236** (236 aa, with signal) | **Glu21–Asp239** (219 aa, mature ECD) | **PENDING_ORGANIZER_CONFIRMATION** (Signal peptide & C-terminal boundary) |

---

## 4. Detailed Biological & Computational Analysis of Conflicts

### 4.1. Track 3: GLP-1R (Glucagon-Like Peptide 1 Receptor)
- **UniProt:** `P43220` (Total length: 463 aa).
- **Chinese Range (Ala21–Glu139, 119 aa):** Represents exclusively the soluble N-terminal extracellular domain (ECD).
  - *Biological Feasibility:* Readily expressed as a soluble secreted construct in mammalian (HEK293) or insect cells for high-throughput surface plasmon resonance (SPR) or bio-layer interferometry (BLI).
  - *Computational Modeling:* Compatible with standard AlphaFold-Multimer and ESMFold2. Avoids hydrophobic TM bundle collapse.
  - *Limitation:* Lacks the 7TM pocket; cannot structurally model deep allosteric agonist insertion into the transmembrane core.
- **English Range (Arg24–Ser432, 409 aa):** Encompasses the ECD plus all seven transmembrane helices (TM1–TM7) and extracellular loops (ECL1–ECL3), ending at intracellular Ser432.
  - *Biological Feasibility:* Requires cell-based functional assays (e.g., cAMP accumulation, GloSensor, or membrane-fraction radioligand binding) or detergent/nanodisc reconstitution.
  - *Computational Risk:* Modeling a soluble VHH against a full 7TM receptor in ESMFold2 without lipid bilayer constraints leads to artificial binding to hydrophobic transmembrane surfaces (false positives).
- **System Stance:** Current configuration uses `Ala21–Glu139` with allosteric epitope steering. Existing candidates are preserved.

### 4.2. Track 6: TNFR1 (Tumor Necrosis Factor Receptor 1)
- **UniProt:** `P19438-1` (Total length: 455 aa).
- **Chinese Range (Met1–Thr211, 211 aa):** Starts at the initiating methionine and includes the 29-residue hydrophobic signal peptide (`MGLSTVPDLLLPLVLLELLVGIYPSGVIGL`).
- **English Range (Leu30–Thr211, 182 aa):** Corresponds exactly to the mature cleaved ectodomain after signal peptide cleavage by signal peptidase.
- **System Stance:** The current local YAML configuration includes residues 1–211 but applies an automated signal peptide mask (`signal_peptide_mask: [1, 29]`). This ensures compatibility with both views: the full sequence is available for alignments, but contacts to residues 1–29 are deducted from ipSAE interface calculations.

### 4.3. Track 7: IL-7Rα (Interleukin-7 Receptor Subunit Alpha / CD127)
- **UniProt:** `P16871-1` (Total length: 459 aa).
- **Chinese Range (Met1–Gly236, 236 aa):** Includes the 20-residue signal peptide (`MTILGTTFGMVFSLLQVVSG`) and terminates at Gly236.
- **English Range (Glu21–Asp239, 219 aa):** Begins at mature Glu21 and extends 3 residues further to Asp239.
- **System Stance:** The system maintains residues 1–236 with `signal_peptide_mask: [1, 20]`. Residues 237–239 (`EED`) represent a juxtamembrane acidic flexible linker that does not participate in cytokine binding.

---

## 5. UniProt, PDB, FASTA & Configuration Audit

| Target | UniProt ID | Reference PDB & Chain | Local FASTA File | Config YAML | Signal Peptide Mask | Oligomeric Context |
|---|---|---|---|---|---|---|
| **EGFR** | P00533 | 6ARU:A | `competition/targets/track_1_egfr.yaml` | Met1–Ser645 | [1, 24] | Monomer / Asymmetric Dimer |
| **TNF-α** | P01375 | 1TNF:A | `competition/targets/track_2_tnfa.yaml` | Val77–Leu233 (157 aa) | None (mature) | Homotrimer |
| **GLP-1R** | P43220 | 6X18:R | `competition/targets/track_3_glp1r.yaml` | Ala21–Glu139 (119 aa) | [1, 3] | Monomer (ECD) / 7TM Complex |
| **TfR1** | P02786 | 11QC:A / 1CX8:A | `competition/targets/track_4_tfr1.yaml` | Cys89–Phe760 (672 aa) | None (ectodomain) | Homodimer |
| **TL1A** | O95150 | 2RE9:A | `competition/targets/track_5_tl1a.yaml` | Leu72–Leu251 (180 aa) | None (mature) | Homotrimer |
| **TNFR1** | P19438-1 | 9S3I:A | `competition/targets/track_6_tnfr1.yaml` | Met1–Thr211 (211 aa) | [1, 29] | Monomer (CRD1–CRD4) |
| **IL-7Rα** | P16871-1 | 3DI3:B | `competition/targets/track_7_il7ra.yaml` | Met1–Gly236 (236 aa) | [1, 20] | Heterodimer (with gamma-c) |

---

## 6. Competition Compliance Gap Analysis

The system was audited against all declared submission and validation rules:

1. **Length Bounds:**
   - Minibinders: 40–100 aa. Strictly validated in `validate_sequence_for_submission`.
   - VHH (Nanobodies): 100–150 aa. Strictly validated in `validate_sequence_for_submission`.
2. **Amino Acid Alphabet:**
   - Only 20 standard natural amino acids (`ACDEFGHIKLMNPQRSTVWY`) are accepted. Any non-standard residue or symbol raises `SecurityIntegrityError`.
3. **Prohibited Tags & Fusion Segments:**
   - Automated detection and fail-closed rejection for: His6-tag (`HHHHHH`), Flag-tag (`DYKDDDDK`), Myc-tag (`EQKLISEEDL`), Strep-tag (`WSHPQFEK`), and terminal GS linkers (`GGGGS`).
4. **De Novo Novelty & Anti-Leakage:**
   - 4-scheme CDR extraction (Chothia, Kabat, IMGT, Martin) enforces 100% intra-pool CDR uniqueness.
   - Nanobody 35 (Nb35) anti-leakage defense rejects any candidate with CDR-H3 sequence identity $\ge 60\%$.
5. **Candidate Library Scoping:**
   - Exactly $\le 20$ candidates exported per team per track.
6. **Submission Packaging:**
   - CSV format: Exactly 1 header (`name,sequence`) + up to 20 candidate rows.
   - Dual-naming support: Standard Unicode filename (`{Target}_submission.csv`) plus ASCII fallback (`{Target_ascii}_submission.csv`).
   - Accompanying documents: `update_note.txt` and `methods_abstract.txt` (< 4,000 characters).

---

## 7. Scientific Screening Compatibility Assessment

The organizer's declared in silico screening configuration:
- **Engine:** ESMFold2
- **Scoring Metric:** ipSAE
- **Hyperparameters:** `num_seeds=1`, `num_samples=1`, `use_templates=False`
- **MSA Mode:** Target has MSA; Designed Binder has NO MSA (single-sequence mode)

**Local Implementation Assessment:**
- The local scorer `ESMFold2_ipSAE_Scorer` in `src/protein_design/predictors/esmfold_ipsae.py` conforms to these exact parameters (`target_msa=True`, `design_msa=False`).
- Heuristic proxy scores generated in offline environments without GPU weights are quarantined under `ScoreProvenance.HEURISTIC_PROXY`.
- Real computational binding confidence cannot be claimed until authentic forward passes are completed on AsterFire.

---

## 8. Existing Artifact Impact Analysis (AsterFire Execution 24000)

1. **Target Prep Artifacts:**
   - Execution 24000 completed target preparation for the 7 targets using the Chinese specification coordinates (`Ala21-Glu139` for GLP-1R, `Met1-Thr211` for TNFR1, `Met1-Gly236` for IL-7Ra).
   - If GLP-1R were changed to `Arg24-Ser432`, the target preparation node would be invalidated, requiring new PDB retrieval (Cryo-EM 7TM receptor) and rebuilding target MSA.
2. **Existing Submissions:**
   - Initial early-claim submissions generated in `submissions/changjiang_cup_2026/` remain valid under the First-come, First-served priority timestamp rule.
   - No submissions will be deleted or overwritten until final confirmation from the organizers.

---

## 9. Test Commands and Reproducible Results

- **Environment:** macOS arm64, Python 3.13.11 (`.venv`).
- **Static Typing Check:** `.venv/bin/mypy src tests` -> `Success: no issues found in 68 source files`.
- **Linter Check:** `.venv/bin/ruff check .` -> `All checks passed!`.
- **Full Test Suite:** `.venv/bin/pytest -q` -> **113 passed in 68.20s** (100% pass rate).

---

## 10. Official Inquiry to Organizing Committee (Bilingual)

To resolve the specification conflicts authoritatively, the following clarification inquiry is prepared for submission to the competition committee (`contact@aiprotein.sjtu.edu.cn`):

### Chinese-Language Clarification Message
```text
尊敬的“长江杯”全球AI蛋白质设计挑战赛组委会专家及技术委员会：

您好！我们是参加本次挑战赛的参赛团队。在研读赛事官方网站（aiprotein.sjtu.edu.cn）发布的赛题指南时，我们在中英文版本中发现了部分靶点氨基酸序列范围（Residue Range）的描述差异。为确保我们的从头设计与后续湿实验评测体系（表达、纯化及亲和力检测）保持严格一致，特向组委会咨询并确认以下具体技术细节：

1. 靶点3（GLP-1R）：
   - 中文页面标注范围为 Ala21-Glu139（胞外结构域 ECD，119 aa，参考PDB: 6X18:R）；
   - 英文页面标注范围为 Arg24-Ser432（包含完整7TM跨膜结构域，409 aa）。
   请问组委会最终湿实验筛选（如SPR/BLI或细胞功能实验）采用的是可溶性ECD蛋白还是全长膜蛋白？在ESMFold2复合物初筛时，评测体系采用的具体靶点FASTA序列范围为何？

2. 靶点6（TNFR1）：
   - 中文页面标注范围为 Met1-Thr211（211 aa，包含N端29 aa疏水信号肽）；
   - 英文页面标注范围为 Leu30-Thr211（182 aa，成熟胞外区）。
   请问评测采用的重组表达构建体是否切除信号肽（即Leu30-Thr211）？

3. 靶点7（IL-7Rα）：
   - 中文页面标注范围为 Met1-Gly236（236 aa，包含20 aa信号肽）；
   - 英文页面标注范围为 Glu21-Asp239（219 aa，成熟胞外区至Asp239）。
   请问评测体系采用的具体N端与C端截断位点为何？

4. 截止时间时区确认：
   请问2026年11月30日 23:59:59 截止时间是否严格以北京时间（UTC+8）为准？

感谢组委会老师和专家的辛勤付出，期待您的权威解答！

参赛团队敬上
```

---

## 11. Target-by-Target Decision Matrix

| Track | Target | Specification Certainty | Local Implementation Status | Decision |
|---|---|---|---|---|
| **1** | **EGFR** | High (Consistent) | VHH generator active, pH 6.0 Histidine enrichment verified. | **GO** |
| **2** | **TNF-α** | High (Consistent) | Minibinder generator active, trimer context accounted for. | **GO** |
| **3** | **GLP-1R** | Medium (Bilingual Conflict) | Soluble ECD active; allosteric agonist mode supported. Full 7TM standby model documented. | **CONDITIONAL GO (Pending Confirmation)** |
| **4** | **TfR1** | High (Consistent) | VHH generator active, homodimer apical epitope accounted for. | **GO** |
| **5** | **TL1A** | High (Consistent) | Minibinder generator active, trimer context accounted for. | **GO** |
| **6** | **TNFR1** | Medium (Signal peptide split) | Ectodomain active with automated signal peptide mask ([1, 29]). | **CONDITIONAL GO (Pending Confirmation)** |
| **7** | **IL-7Rα** | Medium (Signal peptide split) | Ectodomain active with automated signal peptide mask ([1, 20]). | **CONDITIONAL GO (Pending Confirmation)** |

---

## 12. Corrective Action Plan & Next Steps

1. **Maintain Stance:** Keep current target configurations and candidate libraries intact; do not rewrite production files.
2. **Submit Clarification:** Transmit the formal inquiry message to the organizing committee.
3. **Dual-Range Contingency Ready:** If organizers mandate the English range (`Arg24-Ser432` for GLP-1R), activate the prepared 7TM config without delay.
4. **AsterFire Execution 24000:** Await cluster concurrency quota approval before resuming cloud execution.
