# BindCraft Integration Test Plan & Acceptance Protocol

**System:** AI Protein Design System — Changjiang Cup 2026
**Document:** Four-Tier Verification Strategy, Acceptance Gates & Handoff Protocol
**Phase:** Phase 2A — Source-Grounded Design Correction Round
**Target Branch:** `feature/bindcraft-integration`
**Status:** DRAFT SPECIFICATION (Awaiting Review — Zero Breaking Changes)

---

## 1. Stratified Testing Strategy (Tiers A–D)

Testing is strictly stratified into four independent tiers to decouple software parser verification from costly GPU compute infrastructure:

```text
+--------------------------------------------------------------------------------+
|                           TESTING STRATIFICATION                               |
|                                                                                |
|  [Tier A] Fixture Parser Test  --> Static mock output parsing (CPU, NOT MEASURED) |
|  [Tier B] Contract & Error QC  --> Exception isolation, timeout, mock runner   |
|  [Tier C] Runtime Environment  --> Container launch, volume mounts, GPU check  |
|  [Tier D] Real-Tool Smoke Test --> 1 minibinder generated with real AF2/MPNN   |
+--------------------------------------------------------------------------------+
```

### 1.1 Tier A: Fixture Parser Test (Unit Level)
- **Objective:** Verify that canonical candidate sequences (extracted from native column **`Sequence`** in `final_design_stats.csv` or PDB coordinates), converted mmCIF structures, and native score CSV files produced by BindCraft are correctly ingested, transformed, and mapped into `Candidate` and `ProvenanceRecord` objects without syntax errors or data loss.
- **Hardware Requirement:** None (Runs on standard CPU; latency: NOT MEASURED). No GPU required.
- **Prerequisites:** Static test fixture directory containing mock BindCraft outputs (`tests/fixtures/bindcraft_output/`).
- **Target Test File:** `tests/unit/test_bindcraft_parser.py` (To be implemented in Phase 2B).
- **Core Test Cases & Assertions:**
  1. `test_parse_valid_output_directory`: Ingests synthetic candidates; verifies correct extraction of amino acid sequences from native column `Sequence` (cross-verifying that `mpnn_sequence` is recognized as an internal loop variable, not a native CSV header), sequence lengths, and exact numeric extraction of metrics (`Average_pLDDT` on raw 0.0–1.0 float scale, `Average_pTM`, `Average_i_pTM`, `Average_pAE` and `Average_i_pAE` on raw 0.0–1.0 normalized scale rather than Ångströms, `Average_dG` in REU rather than kcal/mol or ddG, `Average_dSASA` in $\text{Å}^2$, `Average_ShapeComplementarity` 0.0–1.0, `Average_PackStat` 0.0–1.0).
     * **Assertion Rule:** Asserts schema correctness and numeric extraction accuracy. **Prohibited from asserting biological quality thresholds** (e.g. must NOT assert `plddt > 80` or `iptm > 0.8` as test pass criteria).
  2. `test_parse_corrupted_scores_csv`: Verifies graceful error raising when CSV columns are missing, non-numeric strings appear in float columns, or delimiters are malformed.
  3. `test_parse_missing_structure_files`: Verifies appropriate exception raising when expected PDB files are missing from `Accepted/`.
  4. `test_parse_rejected_candidates_summary`: Ingests trajectory rejection counters from `failure_csv.csv` and verifies summary counts are attached to `ExperimentRun.output_summary["rejection_counts"]` without creating phantom candidate records.
  5. `test_structure_format_conversion`: Verifies that native `.pdb` files are structurally converted to valid mmCIF files (`binder.cif`, `complex.cif`) rather than simply renaming file extensions.

### 1.2 Tier B: Contract Conformance & Error Handling (Integration Level)
- **Objective:** Validate that `BindCraftGenerator` strictly conforms to the `BaseGenerator` abstract contract, isolates candidate exceptions, respects timeouts, preserves pipeline execution state, and enforces fail-closed export safety separated by purpose.
- **Hardware Requirement:** None (Standard CPU runner).
- **Prerequisites:** Mock subprocess runner injecting simulated exit codes, timeouts, and exceptions.
- **Target Test File:** `tests/integration/test_bindcraft_contract.py` (To be implemented in Phase 2B).
- **Core Test Cases:**
  1. `test_generator_interface_conformance`: Asserts `generator.name == "bindcraft"`, `version == "0.1.0-draft"`, and `generate(target, config, num_candidates, seed)` signature matches the frozen `BaseGenerator` contract.
  2. `test_subprocess_timeout_isolation`: Simulates an unresponsive container process; verifies that the supervisor issues `SIGTERM`, escalates to `SIGKILL` after a 10-second grace period, and marks `ExperimentRun` as `FAILED` or `PARTIAL`.
  3. `test_non_zero_exit_handling`: Simulates container failure (e.g. CUDA OOM exit code 137); verifies detailed `ErrorRecord` capture with stderr trace without crashing the parent pipeline.
  4. `test_sequence_hash_deduplication`: Verifies that candidates with duplicate sequence hashes are marked `CandidateStatus.DUPLICATE` without creating redundant files.
  5. `test_export_guard_blocks_dummy_validated_candidates`: Verifies that `verify_export_safety(candidate, purpose)` enforces:
     * When `purpose="competition"`: Unconditionally blocks candidates that passed only `DummyValidator` or have missing/corrupted structure files; verifies sequence validity; does NOT require `publication_ready = True`.
     * When `purpose="publication"`: Unconditionally blocks candidates lacking `publication_ready = True` or missing any link in the 9-link provenance chain.

### 1.3 Tier C: Runtime & Environment Pre-Flight (Infrastructure Level)
- **Objective:** Verify container engine availability, Docker daemon socket communication, filesystem volume mounts, file permission preservation, and GPU runtime visibility.
- **Hardware Requirement:** Host with Docker/Podman installed; GPU optional (validates graceful reporting when GPU is absent).
- **Prerequisites:** Docker Desktop or Linux container engine operational.
- **Target Test File:** `tests/integration/test_bindcraft_runtime.py` (To be implemented in Phase 2B).
- **Core Test Cases:**
  1. `test_docker_socket_connectivity`: Verifies Docker daemon responds to API ping.
  2. `test_volume_mount_read_write`: Launches a minimal container mounting the temporary workspace to confirm read/write parity across host and container user IDs.
  3. `test_gpu_driver_visibility`: Checks `nvidia-smi` inside container to verify CUDA driver passthrough when GPU mode is enabled.

### 1.4 Tier D: Real-Tool End-to-End Smoke Test (Scientific Level)
- **Objective:** Execute an authentic end-to-end design run generating 1 real minibinder against a known benchmark target (e.g. EGFR or SARS-CoV-2 RBD) using actual AlphaFold2 and ProteinMPNN model weights on an authenticated GPU node.
- **Hardware Requirement:** Dedicated Linux GPU instance (NVIDIA A100 / RTX 4090 / L40S, 24 GB+ VRAM) with CUDA 12+.
- **Prerequisites:** Full BindCraft container image with downloaded AlphaFold2 parameters (~5.3 GB) and ProteinMPNN weights (~50 MB).
- **Target Test File:** `tests/e2e/test_bindcraft_real_smoke.py` (Deferred until dedicated GPU environment is provisioned).
- **Core Test Cases:**
  1. `test_real_minibinder_generation`: Runs 1 design round, produces realistic CIF complex, verifies extracted metric values.
  2. `test_end_to_end_artifact_storage`: Verifies produced artifacts are cleanly persisted into `candidates/{target_id}/{candidate_id}/` and indexed in SQLite DB.
  3. `test_reproducibility_with_seed`: Runs identical target and seed twice; verifies structurally consistent backbone coordinates within GPU floating-point precision bounds.

### 1.5 Strict Scientific Stratification Notice
Following `docs/scientific_principles.md`:
```text
[Real-Tool Execution] != [Artifact Ingestion] != [Computational Metric Passing] != [Wet-Lab Validation]
```
- Passing Tier A and Tier B unit tests validates **data engineering and software parsing only**.
- Passing Tier D real-tool execution validates **computational generation only**.
- Neither computational generation nor dummy validation constitutes **scientific wet-lab proof of binding affinity**.

---

## 2. Section C: Experimental Protocol (Baselines, Ablation, Data Splitting & Leakage Prevention)

To guarantee that the generated binder libraries serve both the Changjiang Cup 2026 competition and a publishable scientific contribution, the following experimental protocol governs all generation and validation campaigns:

### 2.1 Proposed Experimental Baselines (Equal Pool, Equal k, Equal Budget)
To evaluate design and library selection efficacy objectively across identical candidate pools, identical sample size $k$, and identical compute budgets:
1. **Upstream Native Policy (Baseline 1):** Native BindCraft execution using Pacesa et al. (*Nature* 646, 483–492 (2025)) default parameters and ranking policy (sorting accepted candidates by `Average_i_pTM` into `Accepted/Ranked/`).
2. **Metric Top-$k$ Baseline (Baseline 2):** Selection of top-$k$ candidates from the pool based on composite in silico score.
3. **Uniform Random-$k$ Baseline (Baseline 3):** Uniform random sampling of $k$ candidates from the accepted candidate pool.
4. **Multi-Objective Diversity-$k$ (Proposed Method):** Clustering candidates across sequence identity, structural fold, and interface patch to select a non-redundant portfolio of size $k$ (S5).
5. **Orthogonal Generative Baseline (Comparative Future Target):** RFdiffusion backbone generation followed by ProteinMPNN sequence design.

### 2.2 Ablation Study Matrix
To isolate the empirical contribution of each pipeline component, systematic ablation experiments are designed:
- **Ablation A1 (Physics vs. Pure Hallucination):** BindCraft with full PyRosetta FastRelax filtering versus BindCraft with AF2 loss metrics alone (evaluating the empirical necessity of Rosetta physics scoring).
- **Ablation A2 (Hotspot Constraint Weighting):** Systematically varying hotspot loss weights ($\lambda_{\text{hotspot}} = 0.0, 0.5, 1.0, 2.0$) to measure interface focus versus backbone folding quality.
- **Ablation A3 (Sequence Redesign Sampling):** Varying ProteinMPNN sampling temperatures ($T = 0.1, 0.2, 0.5$) and redesign rounds ($N = 1, 3, 5$) to quantify sequence diversity versus structural stability.
- **Ablation A4 (Portfolio Selection vs. Upstream & Top-k Policies):** Comparing multi-objective diversity portfolio selection (S5) against upstream native ranking (`Average_i_pTM`), composite top-$k$, and random-$k$ sampling across structural fold spread and sequence identity distance.

### 2.3 Strict Dataset Partitioning & Anti-Leakage Protocol
Data is partitioned into three strictly segregated sets:
1. **Tuning / Dev Set:** Well-characterized public target proteins with solved high-resolution co-crystal structures (e.g. SARS-CoV-2 RBD [PDB: 6M0J, 2.45 Å], PD-L1 [PDB: 4ZQK, 2.20 Å], or truncated EGFR Domains I-III [PDB: 1MOX, 2.50 Å]). For full-length glycosylated EGFR ectodomain assemblies inherited from the BindCraft publication (specifically PDB: `1IVO` at 3.30 Å and PDB: `1NQL` at 2.80 Å; X-ray diffraction, Ferguson et al. *Mol Cell* 2003), these targets are explicitly documented as historical benchmark exceptions to the strict $\le 2.5\text{ \AA}$ rule, since intact EGFR ectodomain crystals naturally diffract at 2.8–3.3 Å. Used exclusively for calibrating filter thresholds, loss weights, and pipeline hyperparameters.
2. **Exploration Set:** Extended target catalog used for open-ended unconstrained library generation and parameter sensitivity exploration.
3. **Held-Out Test Set:** Sealed evaluation targets (including official Changjiang Cup blind targets) evaluated strictly with frozen configurations.
2. **Exploration Set:** Extended target catalog used for open-ended unconstrained library generation and parameter sensitivity exploration.
3. **Held-Out Test Set:** Sealed evaluation targets (including official Changjiang Cup blind targets) evaluated strictly with frozen configurations.

#### Strict Anti-Leakage Rule (Post-Hoc Overfitting Prohibition):
- **Prohibition on Post-Hoc Tuning:** Under NO circumstances may competition leaderboard rankings, scoring feedback, or experimental wet-lab results from the competition be used to adjust pipeline hyperparameters post-hoc and then re-reported as "independent test performance".
- **Leakage Prevention:** Competition feedback constitutes held-out test data. Any post-competition analysis using this feedback must be explicitly declared as post-hoc exploratory analysis, not independent validation.

### 2.4 Compute, Token & Time Budgets
- **Per-Target Compute Budget:** PROPOSED BUDGET: 8 GPU-hours (NVIDIA A100/L40S equivalent) per target design run (uncalibrated heuristic, subject to empirical measurement).
- **Library Generation Quota:** PROPOSED BUDGET: Default target of $N = 100$ accepted candidates per target, with timeout supervisor capped at 7200 seconds per execution batch (uncalibrated heuristic).
- **Resource Logging:** Total GPU seconds, memory peak, and trajectory rejection counts recorded in `ExperimentRun` metadata.

### 2.5 Evaluation Metrics & Statistical Analysis Plan
- **Primary Computational Metrics:** Distributions of binder pLDDT, complex pLDDT, interface ipTM, interface pAE, PyRosetta $\Delta G$ (REU), SASA ($\text{Å}^2$), and shape complementarity ($S_c$).
- **Library Diversity Metrics:** Pairwise sequence identity distance matrix, unique sequence cluster count at 50% identity threshold, and structural TM-score clustering.
- **Statistical Rigor:** Statistical comparisons across ablation conditions will report median, interquartile ranges, and non-parametric significance tests (Mann-Whitney U test, Kolmogorov-Smirnov test) with Bonferroni correction for multiple comparisons.

### 2.6 Automated Analysis Pipelines & External Baseline Benchmarking Governance (Principles H & J)
- **Principle H (Publication Numbers via Scripted Pipeline):**
  - Manual copying, pasting, or transcribing of numbers into scientific manuscripts, tables, or presentation decks is strictly prohibited.
  - All tables and visualization plots must be generated directly from raw run artifacts stored in `candidates/` and metadata in SQLite via versioned analysis scripts located in `scripts/analysis/`.
  - Every table and figure in research deliverables must record the analysis script SHA and git commit used to generate it.
- **Principle J (External Baseline Benchmarking Rules):**
  - Performance comparisons must adhere strictly to the Four-Tier Verification Taxonomy (`LITERATURE_REPORTED`, `SOURCE_VERIFIED`, `LOCALLY_REPRODUCED`, `PROJECT_BENCHMARKED`).
  - Only `PROJECT_BENCHMARKED` baselines—executed directly within our project framework on identical target definitions, identical evaluation criteria, and identical hardware protocols—can be claimed as baseline performance of project experiments.
  - Literature-reported performance from published papers must be clearly segregated and labeled as `LITERATURE_REPORTED` for external context only.

---

## 3. Formal Acceptance Checklist

```text
+-----------------------------------------------------------------------------------+
|                            PHASE 2A ACCEPTANCE GATE                               |
|                                                                                   |
|  [x] Baseline verification & freeze audit complete                                |
|  [x] Scientific literature grounded in Nature (2025) DOI: 10.1038/s41586-025-09429-6|
|  [x] BindCraft vs BindCraft2 rigorously separated without performance conflation  |
|  [x] Minimal 7-service mapping defined with zero architectural bloat              |
|  [x] Adapter specification complete adhering to Base V1 frozen contract           |
|  [x] 4-Tier test strategy formalized (Tiers A, B, C, D separated)                 |
|  [x] Hard principles A-J on Scientific Integrity & Provenance formalized          |
|  [x] Fail-closed export safety gate designed blocking dummy-validated candidates  |
|  [ ] Adapter implementation & Tier A/B tests (Phase 2B scope)                     |
|  [ ] Design review signed off by Tech Lead / User                                 |
+-----------------------------------------------------------------------------------+
```

### 3.1 Acceptance Matrix & Status Accounting

| Requirement | Verification Criteria | Status | Evidence / Notes |
|---|---|---|---|
| **R1: Baseline Integrity** | Clean git working tree, frozen Base V1 tag `base-v1.0.0` verified, zero changes to core pipeline logic. | **SPECIFICATION_VERIFIED** | Verified via `git status` and `git rev-parse refs/tags/base-v1.0.0`. |
| **R2: Literature Grounding** | Primary paper identified as *Nature* 646, 483–492 (2025) DOI: `10.1038/s41586-025-09429-6`. BindCraft2 separated without performance conflation. | **SPECIFICATION_VERIFIED** | Formally documented in `RESEARCH.md` and `READINESS.md`. |
| **R3: Seven-Service Alignment** | S1 through S7 mapped logically without microservices or multiple databases; existing SQLite and storage reused. | **SPECIFICATION_COMPLETE** | Detailed mapping table documented in `SPECIFICATION.md`. |
| **R4: Adapter Specification** | Full specification of `BindCraftGenerator` including target settings JSON serialization, verified CLI args, runtime isolation, exact metric parsing, and timeout. | **SPECIFICATION_COMPLETE** | Adheres 100% to frozen `BaseGenerator` contract in `SPECIFICATION.md`. |
| **R5: Testing Stratification** | Tiers A, B, C, D strictly separated. Protocol prohibits using Tier A/B to claim Tier D completion. | **SPECIFICATION_COMPLETE** | Testing architecture documented in `TEST_PLAN_AND_HANDOFF.md`. |
| **R6: Scope Limitation** | Zero production code in `src/` modified; no model weights downloaded; no GPU executed; paused cleanly for design sign-off. | **SPECIFICATION_VERIFIED** | Zero changes outside docs directory. |
| **R7: Code Implementation** | Implementation of `src/protein_design/generators/bindcraft.py` and unit test fixtures. | **PENDING_PHASE_2B** | Explicitly deferred to Phase 2B. |
| **R8: Real-Tool GPU Smoke** | Authentic GPU execution of BindCraft with downloaded weights. | **PENDING_GPU_DEPLOYMENT** | Deferred to Tier D on dedicated GPU hardware. |
| **R9: Formal User Sign-Off** | Tech Lead / User review and approval of Phase 2A correction round. | **PENDING_USER_REVIEW** | Required before commencing Phase 2B. |
| **R10: Integrity & Provenance Gate** | Mandatory verification of Principles A through J, 9-link provenance chain, and `publication_ready` boolean check. | **SPECIFICATION_COMPLETE** | Formalized in `RESEARCH.md` §7 and `SPECIFICATION.md` §5. |
| **R11: Fail-Closed Export Guard** | Blocking requirement that `verify_export_safety()` prevents dummy-validated candidates from reaching export paths. | **SPECIFICATION_COMPLETE** | Defined in `SPECIFICATION.md` §4.2 and `TEST_PLAN_AND_HANDOFF.md` §1.2. |

---

## 4. Phase 2A Handoff Protocol

### 4.1 Handoff Declaration
Phase 2A (Research & Readiness Specification) has completed its **Source-Grounded Design Correction Round**.
- All documentation has been aligned with primary literature (*Nature* 646, 483–492 (2025), DOI: `10.1038/s41586-025-09429-6`) and upstream source code (Commit: `06e12a443a5796a798935c13b246a4825946fa7c`).
- Zero production code in `src/` has been altered.
- Zero test files in `tests/` have been altered.
- No model weights have been downloaded; no GPU tasks have been run.
- In accordance with review rules, **Phase 2A is submitted for review and is NOT self-declared as accepted**.

### 4.2 Preconditions for Commencing Phase 2B (Adapter Implementation)
Phase 2B must NOT begin until the user reviews this report and grants explicit authorization:
1. **User Sign-Off on Adapter Design:** Approval of `BindCraftGenerator` interface, JSON settings serialization, runtime boundary, and PDB-to-mmCIF structural conversion strategy.
2. **User Sign-Off on Seven-Service Mapping:** Confirmation that logical domain mapping meets project goals without microservice bloat.
3. **Execution Environment Confirmation:** Confirmation of compute environment plan for Tier D smoke tests (Local WSL2 vs Dedicated Remote Cloud GPU).
4. **Export Safety Sign-Off:** Confirmation of fail-closed guard preventing dummy-validated candidates from entering export pipelines.

Upon receipt of approval, Phase 2B will execute:
- Implementation of `src/protein_design/generators/bindcraft.py`.
- Creation of static mock output fixtures in `tests/fixtures/bindcraft_output/`.
- Implementation of Tier A unit parser tests, Tier B contract tests, and export guard tests in `tests/`.

---

## 5. Section D: Correction Log & Source Evidence Matrix


| Finding ID | Previous Erroneous Claim / Draft Text | Corrected Evidence-Grounded Text | File & Section | Primary Evidence Source | Status | Rationale for Open Status |
|---|---|---|---|---|---|---|
| **FINDING-C1-01** | Cited BindCraft as *Nature Biotechnology* (2024) | Corrected to *Nature* 646, 483–492 (2025). DOI: `10.1038/s41586-025-09429-6`. Title: *One-shot design of functional protein binders with BindCraft*. | `RESEARCH.md` §2, `READINESS.md` §2.1 | Pacesa et al., *Nature* 646 (2025) | **RESOLVED** | N/A |
| **FINDING-C1-02** | BindCraft2 conflated with published experimental affinities | Separated BindCraft2 as Level 6 unvalidated refactor; prohibited performance conflation | `RESEARCH.md` §2, `READINESS.md` §2.2 | PacesaLab/BindCraft2 GitHub repo | **RESOLVED** | N/A |
| **FINDING-C1-03** | Method decision recorded as final with arbitrary `Confidence: 0.90` | Decision categorized as **PROPOSED (Awaiting User Sign-Off)**; removed arbitrary confidence | `RESEARCH.md` §6 | `docs/scientific_principles.md` | **RESOLVED** | N/A |
| **FINDING-C2-01** | Upstream repository unpinned | Pinned full commit SHA `06e12a443a5796a798935c13b246a4825946fa7c` | `RESEARCH.md` §2, `SPECIFICATION.md` §3.1 | `martinpacesa/BindCraft` git log | **RESOLVED** | N/A |
| **FINDING-C3-01** | Assumed PDB files could be stored as CIF by changing file extension | Mandated structural conversion via Gemmi/BioPython parser | `SPECIFICATION.md` §3.5 | Base V1 storage contract | **RESOLVED** | N/A |
| **FINDING-C4-01** | Predicted computational metrics conflated with binding affinity | Explicitly classified pLDDT, i_pTM, dG as computational predictions, not wet-lab Kd | `RESEARCH.md` §3.3, `SPECIFICATION.md` §3.5 | `docs/scientific_principles.md` | **RESOLVED** | N/A |
| **FINDING-C5-01** | Presumed competition participation satisfies academic PyRosetta license | Updated administrator to Univ. of Washington; flagged that sponsored competitions require case-specific clearance | `RESEARCH.md` §4.2 | Univ. of Washington CoMotion license | **RESOLVED** | N/A |
| **FINDING-C5-02** | Claimed `--no-pyrosetta` OpenMM fallback mode was ready | Marked `--no-pyrosetta` as **DEFERRED / UNVERIFIED IN UPSTREAM** | `RESEARCH.md` §4.2, `SPECIFICATION.md` §3.3 | BindCraft upstream source code | **RESOLVED** | N/A |
| **FINDING-C5-03** | Claimed 4GB VRAM GPU could support minibinders up to 60 AAs | Removed unsubstantiated VRAM commitments pending empirical benchmark measurements | `READINESS.md` §3.2 | Hardware profiling principles | **RESOLVED** | N/A |
| **FINDING-C7-01** | Equated database cache hit with seed-based algorithmic reproducibility | Decoupled cache hit from seed reproducibility on GPU hardware | `SPECIFICATION.md` §3.8 | Determinism principles | **RESOLVED** | N/A |
| **FINDING-C8-01** | Parser unit tests hardcoded biological quality thresholds (pLDDT > 80) | Removed biological thresholds from parser tests; focused on schema & numeric accuracy | `TEST_PLAN_AND_HANDOFF.md` §1.1 | Unit testing principles | **RESOLVED** | N/A |
| **FINDING-C8-02** | Acceptance checklist marked items as [x] PASSED prior to implementation | Replaced with transparent statuses (`SPECIFICATION_COMPLETE`, `PENDING_IMPLEMENTATION`) | `TEST_PLAN_AND_HANDOFF.md` §3 | Quality governance | **RESOLVED** | N/A |
| **FINDING-C9-01** | Absence of formal scientific integrity and data ownership governance | Established Principles A through J, 9-link provenance chain, and `PUBLICATION_READY` gate | `RESEARCH.md` §7, `SPECIFICATION.md` §6 | Scientific integrity rules | **RESOLVED** | N/A |
| **FINDING-C10-01** | Simulated CLI arguments (`--pdb`, `--lengths`, `--seed`) not supported in upstream `bindcraft.py` | Corrected CLI interface to `--settings`, `--filters`, `--advanced`; mapped all parameters into JSON | `RESEARCH.md` §3.2, `SPECIFICATION.md` §3.3 | Upstream `bindcraft.py` argparse | **RESOLVED** | N/A |
| **FINDING-C11-01** | Assumed Base seed controls entire pipeline and claimed framework determinism | Cited upstream dynamic seed `np.random.randint`; documented Base seed does not control end-to-end without wrapper; removed determinism claims; disentangled 5 seed concepts | `RESEARCH.md` §3.4, `SPECIFICATION.md` §3.8 | Upstream `bindcraft.py` source (line 91) | **RESOLVED** | N/A |
| **FINDING-C12-01** | Assumed native `Accepted/final_designs.fasta` and column name `mpnn_sequence` | Identified exact native column header `Sequence` (capitalized); recognized `mpnn_sequence` is Python variable only; FASTA made optional downstream | `RESEARCH.md` §3.3, `SPECIFICATION.md` §3.5 | Upstream `generic_utils.py` line 29 | **RESOLVED** | N/A |
| **FINDING-C13-01** | Conflated Rosetta $\Delta G$ with `ddG` and described REU as kcal/mol | Preserved exact native column `Average_dG` (REU); prohibited describing REU as kcal/mol or ddG | `RESEARCH.md` §3.3, `SPECIFICATION.md` §3.5 | Upstream `generic_utils.py` & `pyrosetta_utils.py` | **RESOLVED** | N/A |
| **FINDING-C14-01** | Misstated EGFR PDB `1NQL` resolution as 2.40 Å; misattributed BindCraft2 license | Corrected `1NQL` resolution to 2.80 Å (RCSB X-ray); classified full-length EGFR ectodomain as documented historical benchmark exception; corrected BindCraft2 license to source-available hosting-restricted | `RESEARCH.md` §1.2, §4.1, `TEST_PLAN_AND_HANDOFF.md` §2.3 | RCSB PDB structure `1NQL` & Pacesa Lab repo | **RESOLVED** | N/A |
| **FINDING-C15-01** | Used inaccurate target settings JSON keys (`"pdb"`, `"target_chains"`) | Established exact upstream keys: `"starting_pdb"`, `"chains"`, `"target_hotspot_residues"`, `"lengths"`, `"number_of_final_designs"`, `"binder_name"`, `"design_path"` | `SPECIFICATION.md` §3.3 | `settings_target/PDL1.json` & `bindcraft.py` | **RESOLVED** | N/A |
| **FINDING-C16-01** | Conflated native metric columns with informal aliases (`pLDDT`, `i_pTM`, `interface_dG`, `interface_sc`) | Established exact native CSV headers: `Average_pLDDT`, `Average_i_pTM`, `Average_i_pAE`, `Average_dG`, `Average_ShapeComplementarity`, `Average_PackStat`, etc. | `RESEARCH.md` §3.3, `SPECIFICATION.md` §3.5 | `functions/generic_utils.py` lines 16–38 | **RESOLVED** | N/A |
| **FINDING-C17-01** | Assumed pLDDT is 0–100 and pAE is in Ångströms natively | Identified native ColabDesign scales: pLDDT is 0.0–1.0 float; pAE and i_pAE are normalized (0.0–1.0, dimensionless); separated raw upstream vs transformed Base V1 representation | `RESEARCH.md` §3.3, `SPECIFICATION.md` §3.5 | `colabdesign_utils.py` & `default_filters.json` | **RESOLVED** | N/A |
| **FINDING-C18-01** | Export safety guard forced `publication_ready = True` for all exports including competition | Separated `verify_export_safety(candidate, purpose)` into `competition` (eligibility rules, dummy-blocking) and `publication` (requires `publication_ready = True`) | `SPECIFICATION.md` §4.2, `READINESS.md` §7 | Scientific integrity protocols | **RESOLVED** | N/A |
| **FINDING-C19-01** | Missing comprehensive inventory of upstream rejected design data | Documented exact upstream rejected data assets: `failure_csv.csv`, `trajectory_stats.csv`, `mpnn_design_stats.csv`, `Trajectory/LowConfidence/`, `Trajectory/Clashing/`, `Rejected/*.pdb` | `RESEARCH.md` §3.5, `SPECIFICATION.md` §3.6 | Upstream `bindcraft.py` line 427 & `generic_utils.py` | **RESOLVED** | N/A |
| **FINDING-C20-01** | Stale licensing administrator for PyRosetta (`Johns Hopkins University`) in readiness table | Updated official licensing administrator to University of Washington (CoMotion / RosettaCommons) | `READINESS.md` §5.1, `RESEARCH.md` §4.1 | UW CoMotion license agreement | **RESOLVED** | N/A |



