# CHANGJIANG CUP 2026 — CRITICAL AUDIT CORRECTION & SERIAL EXECUTION RECOVERY (V3)

**Project:** AI Protein Design System  
**Campaign Branch:** `feature/changjiang-cup-2026`  
**Reference Cloud Execution:** AsterFire Execution 24000 (Plan 22425, Cluster `SAI-compute-NEW`)  
**Audit Timestamp:** 2026-11-06T16:01:00+07:00  
**Lead Auditor:** Houhou (Front Agent & Tech Lead, MyAgent)  
**Status:** Verification & Specification Correction Complete — CONDITIONAL GO with Serial Recovery Readiness  

---

## 1. Executive Summary

This audit report delivers a rigorous, evidence-grounded correction of the competition specifications for the **Changjiang Cup 2026 (Global AI Protein Design Challenge)**, establishes single-task serial recovery protocol for the AsterFire cloud compute platform under **Personal Mode**, and provides a definitive revalidation of all competition targets, candidate sequences, and submission packages.

### 1.1. Key Findings & Actions Completed
1. **Critical Target Classification Correction (TNF-α):**
   - The previous report draft (`CHANGJIANG_2026_OFFICIAL_RULES_RECONCILIATION_V2.md`) mistakenly listed Track 2 (TNF-α) as a Minibinder (40–100 aa).
   - The official competition specifications define **TNF-α as a VHH (Nanobody, 100–150 aa)**.
   - Comprehensive audit of the codebase revealed that the underlying YAML configuration (`track_2_tnfa.yaml`), the generator routing (`VHHScaffoldGenerator`), the SQLite database records, and the exported submission package (`submissions/TNF-alpha_submission.csv`) were **already implemented as VHH**.
   - The discrepancy was an isolated editorial/clerical error in the previous report's summary table. All 10 candidate sequences in the database were revalidated: lengths range from 108 to 117 aa, strictly compliant with VHH rules.
2. **Official Seven-Target Specification Alignment:**
   - 5 VHH tracks: Track 1 (EGFR), Track 2 (TNF-α), Track 3 (GLP-1R), Track 4 (TfR1), Track 6 (TNFR1).
   - 2 Minibinder tracks: Track 5 (TL1A), Track 7 (IL-7Rα).
3. **Official Contact Email Verified:**
   - The official inquiry channel has been confirmed as `zbztzhz@sjtu.edu.cn`.
4. **AsterFire Single-Task Serial Execution Readiness (Personal Mode):**
   - The system is configured for Personal Mode with strict single-task concurrency (`max_concurrency=1`), eliminating the dependency on quota escalation or Team Mode migration.
   - The target preparation chain for `1TNF` (TNF-α) is complete and cached.
   - The single GPU validation node `esmfold_target_tnfa` has been fully scoped and prepared for isolated execution without launching the 140 decoy tasks.

---

## 2. Corrected Seven-Target Specification Matrix

| Track | Target Identifier | Official Molecule Type | Target Length Bounds | Target Sequence Range (Chinese / Portal) | Target Sequence Range (English Portal) | Status in Local System |
|---|---|---|---|---|---|---|
| **1** | **EGFR** | **VHH (Nanobody)** | 100–150 aa | Met1–Ser645 | Leu25–Ser645 | **CONFIRMED** (Signal peptide masked: 1–24) |
| **2** | **TNF-α** | **VHH (Nanobody)** | 100–150 aa | Val77–Leu233 (157 aa) | Val77–Leu233 | **CONFIRMED & CORRECTED** (VHH scaffold active, 108–117 aa) |
| **3** | **GLP-1R** | **VHH (Nanobody)** | 100–150 aa | **Ala21–Glu139** (119 aa, ECD) | **Arg24–Ser432** (409 aa, ECD+7TM) | **PENDING_ORGANIZER_CONFIRMATION** |
| **4** | **TfR1** | **VHH (Nanobody)** | 100–150 aa | Cys89–Phe760 (672 aa) | Cys89–Phe760 | **CONFIRMED** (Homodimer apical epitope) |
| **5** | **TL1A** | **Minibinder** | 40–100 aa | Leu72–Leu251 (180 aa) | Leu72–Leu251 | **CONFIRMED** (Homotrimer context) |
| **6** | **TNFR1** | **VHH (Nanobody)** | 100–150 aa | **Met1–Thr211** (211 aa) | **Leu30–Thr211** (182 aa) | **PENDING_ORGANIZER_CONFIRMATION** (Signal masked: 1–29) |
| **7** | **IL-7Rα** | **Minibinder** | 40–100 aa | **Met1–Gly236** (236 aa) | **Glu21–Asp239** (219 aa) | **PENDING_ORGANIZER_CONFIRMATION** (Signal masked: 1–20) |

---

## 3. Root Cause Analysis: TNF-α Classification

### 3.1. Investigation Findings
An investigation was conducted across all files to trace the origin of the "Minibinder" label for TNF-α:

1. **Target Specification File (`competition/targets/track_2_tnfa.yaml`):**
   - Lines 44–47:
     ```yaml
     metadata:
       track_id: 2
       molecule_type: VHH
       min_length: 100
       max_length: 150
     ```
   - *Status:* Correctly configured as VHH from inception.
2. **Generator Routing (`src/protein_design/core/campaign.py`):**
   - Line 83 routes `molecule_type: VHH` to `VHHScaffoldGenerator()`.
   - *Status:* Correctly executed `VHHScaffoldGenerator`.
3. **Database Inspection (`protein_design.db`):**
   - Querying the 10 stored TNF-alpha candidate records:
     - `tnfalpha_vhh_000001`: Length 110 aa, generator `vhh_scaffold`
     - `tnfalpha_vhh_000002`: Length 117 aa, generator `vhh_scaffold`
     - `tnfalpha_vhh_000003`: Length 113 aa, generator `vhh_scaffold`
     - `tnfalpha_vhh_000004`: Length 117 aa, generator `vhh_scaffold`
     - `tnfalpha_vhh_000005`: Length 117 aa, generator `vhh_scaffold`
     - `tnfalpha_vhh_000006`: Length 108 aa, generator `vhh_scaffold`
     - `tnfalpha_vhh_000007`: Length 116 aa, generator `vhh_scaffold`
     - `tnfalpha_vhh_000008`: Length 110 aa, generator `vhh_scaffold`
     - `tnfalpha_vhh_000009`: Length 117 aa, generator `vhh_scaffold`
     - `tnfalpha_vhh_000010`: Length 115 aa, generator `vhh_scaffold`
   - *Status:* 100% of generated candidates are authentic VHH nanobodies.
4. **Root Cause Conclusion:**
   - The misclassification was purely an editorial error in the Markdown text of `CHANGJIANG_2026_OFFICIAL_RULES_RECONCILIATION_V2.md`, where the author inadvertently copied the "Minibinder" row descriptor into Track 2.
   - In addition, `tests/unit/test_submission.py` had a mock unit test named `test_generate_submission_rolling_and_fallback` that happened to pass a dummy 60-aa sequence labeled "TNF-α" as a test fixture. This test fixture has now been updated to use a canonical 118-aa VHH sequence.

---

## 4. Exact Modifications & Test Evidence

### 4.1. File Changes
| File Path | Nature of Change | Traceable Detail |
|---|---|---|
| `docs/reports/CHANGJIANG_2026_OFFICIAL_RULES_RECONCILIATION_V2.md` | Audit Correction | Updated table row 2 and decision matrix row 2 to define TNF-α as VHH (100–150 aa); updated official contact email to `zbztzhz@sjtu.edu.cn`. |
| `src/protein_design/core/campaign.py` | Engine Hardening | Enhanced `load_target()` with fuzzy normalization (`search_norm`) and inner YAML inspection, seamlessly matching `TNF-alpha`, `tnfa`, `track_2`, or track ID `2`. |
| `tests/unit/test_submission.py` | Test Fixture Alignment | Replaced 60-aa mock sequence with authentic 118-aa VHH sequence for TNF-α submission tests. |
| `tests/unit/test_vhh_and_campaign.py` | Regression Test Addition | Added `test_tnfa_track_vhh_campaign_execution` explicitly testing end-to-end TNF-α execution via `VHHScaffoldGenerator`, validating length (100–150 aa) and 2 canonical Cysteines. |

### 4.2. Test Execution Evidence
- **Targeted Test Suite:**
  ```bash
  .venv/bin/pytest tests/unit/test_submission.py tests/unit/test_vhh_and_campaign.py -q
  ```
  *Output:* `10 passed in 1.80s` (100% pass rate).
- **Full Test Suite:**
  ```bash
  .venv/bin/pytest -q
  ```
  *Output:* `114 passed in 71.12s` (100% pass rate, zero failures).
- **Static Typing & Linter:**
  ```bash
  .venv/bin/ruff check .
  .venv/bin/mypy src tests
  ```
  *Output:* All checks passed; 0 Ruff errors; 0 Mypy typing issues across 68 source files.

---

## 5. Existing Candidate & Submission Impact Analysis

### 5.1. Revalidation of TNF-α Candidates
Each of the 10 candidate sequences stored in `protein_design.db` for target `TNF-alpha` was subjected to strict revalidation via `validate_sequence_for_submission(cand.sequence, molecule_type="VHH")`:

| Candidate ID | Sequence Length | Canonical Cysteines | Prohibited Tags Check | VHH Range [100, 150] | Status |
|---|---|---|---|---|---|
| `tnfalpha_vhh_000001` | 110 aa | Exactly 2 | None (Clean) | Valid | **PASS** |
| `tnfalpha_vhh_000002` | 117 aa | Exactly 2 | None (Clean) | Valid | **PASS** |
| `tnfalpha_vhh_000003` | 113 aa | Exactly 2 | None (Clean) | Valid | **PASS** |
| `tnfalpha_vhh_000004` | 117 aa | Exactly 2 | None (Clean) | Valid | **PASS** |
| `tnfalpha_vhh_000005` | 117 aa | Exactly 2 | None (Clean) | Valid | **PASS** |
| `tnfalpha_vhh_000006` | 108 aa | Exactly 2 | None (Clean) | Valid | **PASS** |
| `tnfalpha_vhh_000007` | 116 aa | Exactly 2 | None (Clean) | Valid | **PASS** |
| `tnfalpha_vhh_000008` | 110 aa | Exactly 2 | None (Clean) | Valid | **PASS** |
| `tnfalpha_vhh_000009` | 117 aa | Exactly 2 | None (Clean) | Valid | **PASS** |
| `tnfalpha_vhh_000010` | 115 aa | Exactly 2 | None (Clean) | Valid | **PASS** |

### 5.2. Submission File Integrity
The existing submission package files:
- `submissions/TNF-alpha_submission.csv`
- `submissions/TNF-a_submission.csv`
- `submissions/TNF-alpha_methods_abstract.txt`
- `submissions/TNF-alpha_update_note.txt`

Already contain valid VHH designs and explicitly state:
> *"De Novo Architecture: Candidates engineered de novo via generative pipelines (VHH, strictly within 100-150 aa). Zero template grafting."*

**Conclusion:** No candidate sequences or submission files require re-generation or deletion. All existing TNF-α candidates are 100% compliant with the official VHH competition rules.

---

## 6. Status of the Three Unresolved Bilingual Target Conflicts

The three target range conflicts remain classified as `PENDING_ORGANIZER_CONFIRMATION`:

1. **Target 3 (GLP-1R):**
   - Chinese: `Ala21–Glu139` (119 aa, soluble ECD).
   - English: `Arg24–Ser432` (409 aa, full ECD+7TM).
   - *Policy:* Retain `Ala21–Glu139` configuration. Standby 7TM FASTA prepared.
2. **Target 6 (TNFR1):**
   - Chinese: `Met1–Thr211` (211 aa, full precursor).
   - English: `Leu30–Thr211` (182 aa, mature cleaved ectodomain).
   - *Policy:* Retain 1–211 with `signal_peptide_mask: [1, 29]`.
3. **Target 7 (IL-7Rα):**
   - Chinese: `Met1–Gly236` (236 aa, full precursor).
   - English: `Glu21–Asp239` (219 aa, mature cleaved ectodomain).
   - *Policy:* Retain 1–236 with `signal_peptide_mask: [1, 20]`.

Official inquiry message targeting `zbztzhz@sjtu.edu.cn` has been finalized and queued for dispatch.

---

## 7. AsterFire Execution 24000 Single-Task Serial Recovery

### 7.1. Personal Mode Strategy (`max_concurrency=1`)
The user has selected **Personal Mode** on AsterFire. Key operational guidelines:
- Work within the confirmed single concurrent task limit (`max_concurrency=1`).
- No quota escalation request or Team Mode migration is required.
- Do NOT resume the entire 41-node workflow or launch the 140 decoy subtasks, which would saturate the queue and trigger infrastructure holds.

### 7.2. Status of Execution 24000
- **Target Preparation (7/7):** `fetch_1tnf` -> `extract_1tnf` -> `pdbfixer_1tnf` completed successfully and cached in cloud object storage.
- **Aggregation Node:** `chain_extract` completed and cached.
- **Compute Slot Status:** The single personal compute slot on `SAI-compute-NEW` is currently idle/free.

### 7.3. Scoping of Single-Node Task: `esmfold_target_tnfa`
To validate GPU execution under Personal Mode safely, `esmfold_target_tnfa` is selected as the pilot single-node job:
1. **Objective:** Execute ESMFold2 forward pass on the isolated TNF-α monomer receptor chain (157 aa) to verify target pLDDT, GPU memory allocation, and output tensor formatting.
2. **Input Dependencies:**
   - Input structure: Output of `chain_extract` for `1TNF` (already cached).
   - Input sequence: Val77–Leu233 of UniProt P01375 (157 aa).
   - Target MSA: UniProt P01375 alignment (MSA enabled for target).
3. **Safety Constraints:**
   - Submit exactly 1 node (`esmfold_target_tnfa`).
   - Do NOT submit downstream candidate scoring complexes.
   - Do NOT launch the 20 decoy complexes for track 2.
4. **Estimated StarCoin Consumption:**
   - ~5–10 StarCoins for a single 157-aa monomer forward pass.
   - Real expenditure will be logged and verified upon task completion.

---

## 8. Final Decision Matrix

| Evaluation Dimension | Evidence & Verification | Status | Decision |
|---|---|---|---|
| **1. Target Specifications** | 5 VHH tracks + 2 Minibinder tracks aligned with official portal; TNF-α VHH confirmed. | Verified | **GO** |
| **2. Candidate Library Integrity** | All 10 TNF-α candidates revalidated as valid VHH (108–117 aa); 0 non-standard residues; 0 tags. | Verified | **GO** |
| **3. Submission Packaging** | Export safety gates active; CSV files and abstracts reflect VHH de novo design. | Verified | **GO** |
| **4. AsterFire Serial Recovery** | Personal Mode protocol formulated; single-node `esmfold_target_tnfa` scoped. | Ready | **GO (Single-Node Serial)** |
| **5. Bilingual Target Conflicts** | GLP-1R, TNFR1, and IL-7Rα conflicts isolated under `PENDING_ORGANIZER_CONFIRMATION`. | Controlled | **CONDITIONAL GO (Pending Confirmation)** |

---

## 9. Next Steps

1. Transmit the bilingual clarification email to `zbztzhz@sjtu.edu.cn`.
2. Under user confirmation, dispatch `esmfold_target_tnfa` as a single isolated job on AsterFire in Personal Mode.
3. Record real StarCoin consumption and verify output PDB/pLDDT metrics upon completion.
