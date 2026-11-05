# Model Integration Readiness & System Architecture Audit

**System:** AI Protein Design System — Changjiang Cup 2026
**Document:** Model Integration Readiness & Baseline Audit
**Phase:** Phase 2A — Source-Grounded Design Correction Round
**Target Branch:** `feature/bindcraft-integration`
**Baseline Git Tag:** `base-v1.0.0` (Commit: `0f52d9f16bbd2413b909f86bbfd731c113ad0bcd`, Tag Object: `08bc714c355a3dbba25d305623a53e06464ff2f4`)
**Status:** DRAFT SPECIFICATION (Awaiting Review — Zero Breaking Changes)

---

## 1. Executive Summary & Base V1 Baseline Integrity

This readiness audit establishes the formal boundary conditions and architectural contracts for integrating automated de novo binder design engines into the AI Protein Design System.

### 1.1 Factual Baseline Status
- **Repository Location:** `/Users/haohg/Project/AI-Protein-Design-System`
- **Active Branch:** `feature/bindcraft-integration`
- **Frozen Base V1 Commit:** `0f52d9f16bbd2413b909f86bbfd731c113ad0bcd` (tagged as annotated tag `base-v1.0.0`)
- **Current Adapter Code:** **None (Zero real model adapters exist in `src/protein_design/generators/`)**. Only `DummyGenerator`, `DummyPredictor`, and `DummyValidator` exist in `src/`.
- **Model Checkpoints Downloaded:** **None (Zero AlphaFold2 or ProteinMPNN weights downloaded)**.
- **Real Tool Executions:** **None (Zero real GPU runs executed in this repository)**.

### 1.2 Frozen Core Contracts (Base V1 Invariants)
Following `docs/BASE_V1_FREEZE.md`, the core execution contracts are strictly frozen:
1. **Generator Contract (`BaseGenerator`):**
   ```python
   def generate(self, target: Target, config: dict[str, Any], num_candidates: int, seed: int) -> list[Candidate]
   ```
2. **Predictor Contract (`BasePredictor`):**
   ```python
   def predict(self, candidate: Candidate, target: Target, config: dict[str, Any]) -> PredictionResult
   ```
3. **Validator Contract (`BaseValidator`):**
   ```python
   def validate(self, candidate: Candidate, config: dict[str, Any]) -> ValidationResult
   ```
4. **Lifecycle State Machine:** Strict transitions in `src/protein_design/core/lifecycle.py`:
   `CREATED` -> `GENERATED` -> `SEQUENCE_VALIDATED` -> `STRUCTURE_PREDICTED` -> `STRUCTURE_CHECKED` -> `INTERFACE_CHECKED` -> `DEVELOPABILITY_CHECKED` -> `NOVELTY_CHECKED` -> `VALID`.
   Terminal states: `VALID`, `REJECTED`, `FAILED`, `INVALID`, `DUPLICATE`.
5. **Persistence & Layout:** SQLite metadata store with WAL mode (`protein_design.db`) and filesystem artifact layout `candidates/{target_id}/{candidate_id}/` (storing `sequence.fasta`, `binder.cif`, `complex.cif`, `provenance.json`).
6. **Config-First Policy:** No hardcoded scientific thresholds in code; all thresholds default to `null` ("compute but do not filter until calibrated").

### 1.3 Dual-Track Project Objectives: Competition & Scientific Publication
The AI Protein Design System serves two concurrent, co-equal missions:
1. **Competition Deliverable (Changjiang Cup 2026):** Production of high-diversity, rule-compliant candidate binder libraries targeting designated competitive epitopes.
2. **Scientific Publication Deliverable:** Production of rigorous, publication-grade research assets, transparent ablation benchmarks, and verifiable negative design space data suitable for peer-reviewed journal submission.

**Architectural Directives & Hard Principles (Principles A through J):**
- **Strict Integrity Governance:** All scientific results must strictly adhere to the 10 Hard Principles (`RESEARCH.md` §7): No Fabricated Data (A), No Result Misattribution (B), Self-Generated Results with 9-Link Provenance (C), Experimental Attribution (D), Six-Category Failure Retention (E), Competition/Research Track Separation (F), Public Data Governance (G), Scripted Publication Numbers (H), Scientific Integrity & Provenance Gate (I), and Four-Tier External Baselines Taxonomy (J).
- **Track Separation Policy:** Competition Track is permitted to dynamically adapt and optimize candidate portfolios to maximize competition outcomes; Research Track operates under a strict protocol freeze. Competition feedback cannot be recycled as held-out test evidence.
- **Dual Mission Safeguard:** Publication protocols govern reporting rigor, attribution, and provenance verification; they do not restrict the candidate exploration space or diversity of the Competition Track.
- **Multi-Tool Plumbing:** Multi-tool packaging and seven-service architecture are engineering plumbing, not scientific novelty.
- **Scientific Novelty Focus:** Scientific novelty is hypothesized and evaluated through multi-objective diversity portfolio tracking and decoupled validation rigor.

### 1.4 Zero-Breaking-Change Mapping Matrix

| Base V1 Subsystem | Frozen Invariant | Phase 2A/2B Integration Approach | Breaking Change Risk |

|---|---|---|---|
| **Pipeline Coordinator** | `Pipeline.run()` orchestrates generators, predictors, validators | Adapter `BindCraftGenerator` fulfills `BaseGenerator` polymorphically | ZERO (Untouched) |
| **Data Schemas** | `Candidate`, `Target`, `ExperimentRun`, `ProvenanceRecord` | Reused directly; BindCraft metadata mapped into unreserved fields | ZERO (Untouched) |
| **Lifecycle States** | Explicit enum `CandidateStatus` | Candidates initialized to `GENERATED`; no new lifecycle states added | ZERO (Untouched) |
| **Storage Engine** | `MetadataStore` (SQLite) & `ArtifactStore` (Filesystem) | Reused directly; artifacts converted from PDB to canonical mmCIF | ZERO (Untouched) |

---

## 2. Scientific Foundation & Literature Grounding

### 2.1 Primary Scientific Source
- **Publication Title:** *One-shot design of functional protein binders with BindCraft*
- **Authors:** Martin Pacesa, Marc F. Bonet, Andreas Loukas, Carlos G. H. R. D. B. Pires, et al.
- **Journal:** *Nature* 646, 483–492 (2025)
- **DOI:** `10.1038/s41586-025-09429-6`
- **Primary Upstream Repository:** `https://github.com/martinpacesa/BindCraft`
- **Upstream Locked Commit SHA:** `06e12a443a5796a798935c13b246a4825946fa7c`

### 2.2 Strict Distinction: BindCraft Original vs BindCraft2
Following the core scientific principle **"AI Output Is Not Truth"** (`docs/scientific_principles.md`):

| Evaluation Dimension | BindCraft (Original Pipeline) | BindCraft2 (Next-Gen Initiative) |
|---|---|---|
| **Primary Citation** | Martin Pacesa et al., *Nature* 646, 483–492 (2025). DOI: `10.1038/s41586-025-09429-6` | Pacesa Lab GitHub repository (`https://github.com/PacesaLab/BindCraft2`) |
| **Evidence Level** | **Level 3 (Peer-reviewed journal paper)** with extensive wet-lab validation (SPR, cryo-EM, binding assays) | **Level 6 (Model documentation / GitHub repo)** in active development/refactoring |
| **Algorithmic Protocol** | AF2 Hallucination + ProteinMPNN sequence design + PyRosetta interface relaxation + AF2/ColabFold validation | Refactored modular pipeline, alternative predictors, revised configuration formats |
| **Empirical Status in This Repo** | Architecture analyzed, test fixture schemas designed. **Zero empirical runs.** | Investigated as potential future backend. **Zero benchmarks or runs.** |
| **Performance Claims Boundary** | Reported picomolar/nanomolar affinities apply **strictly** to the published BindCraft protocol. | **PROHIBITED** from conflating BindCraft2 with published *Nature* 2025 experimental affinities. |

### 2.3 Evidence Hierarchy Taxonomy (docs/scientific_principles.md)
Every scientific statement, parameter choice, and validation claim in this system must be anchored to this evidence taxonomy:
- **Level 1:** Experimental wet-lab evidence (Binding assays, SPR, Cryo-EM).
- **Level 2:** Experimental databases (PDB structures, curated public databases).
- **Level 3:** Peer-reviewed journal publications (*Nature*, *Science*, *Cell*).
- **Level 4:** Independent computational evidence (Cross-validated by distinct algorithmic models).
- **Level 5:** Preprints (bioRxiv, arXiv).
- **Level 6:** Model documentation and source code repositories (README, release tags).
- **Level 7:** AI reasoning and generative predictions (Least reliable; cannot serve as standalone proof).

---

## 3. Hardware & Runtime Readiness Reality

### 3.1 Three-Tier Runtime Environment Classification
To eliminate ambiguous hardware assumptions, runtime environments are explicitly classified:

| Runtime Classification | Hardware Specification | BindCraft Compatibility | Role & Boundaries in System |
|---|---|---|---|
| **Development Host (Current)** | macOS Apple Silicon / Darwin (Python 3.11/3.13) | Incompatible with native CUDA/JAX/PyRosetta | **Development & Orchestration**: Runs Base V1 core CLI, SQLite DB, mock fixture parsing (Tier A/B). |
| **Secondary Local Node (Historical)** | Windows 11 / WSL2 / RTX 3050 (4 GB VRAM) | Severely VRAM-constrained | **Small Minibinder Smoke Checks Only**: 4GB VRAM causes CUDA OOM on standard AF2 complexes. Zero empirical benchmarks executed. |
| **Target Production Runtime** | Dedicated Linux Instance (NVIDIA A100 / RTX 4090, 24 GB+ VRAM) | **Fully Supported** | **Production Generation Node**: Required for authentic full-length target hallucination and batch runs (Tier D). |
| **Executed Runtime to Date** | None | N/A | **Zero real GPU executions have occurred in this repository.** |

### 3.2 Removal of Unsubstantiated VRAM & Length Commitments
- **Correction:** Prior draft documentation stated that a 4 GB VRAM GPU could support minibinders up to 60 amino acids.
- **Evidence-Grounded Policy:** This assertion is **removed**. AlphaFold2 backpropagation memory footprint depends heavily on target sequence length, crop size, recycling iterations, and Evoformer activation memory. No empirical profiling has been conducted on local hardware; therefore, no VRAM-versus-length guarantees are made without empirical benchmark data.

### 3.3 Subprocess Container Isolation Pattern
```text
+---------------------------------------------------------------------------------+
|  Host Operating System (macOS / Linux / Windows)                                |
|  - AI Protein Design System Core (Base V1 Frozen Pipeline)                      |
|  - SQLite Metadata DB (protein_design.db) & ArtifactStore                       |
|                                                                                 |
|  BindCraftGenerator (BaseGenerator Adapter)                                    |
|       │                                                                         |
|       ├── Mode = "mock"         --> Ingests static mock output fixtures (Tier A)|
|       ├── Mode = "docker"       --> Executes local container via Subprocess     |
|       └── Mode = "cloud_runner" --> Deferred to post-Phase 2                    |
+---------------------------------------│-----------------------------------------+
                                        │ Subprocess CLI / Volume Mount
+---------------------------------------▼-----------------------------------------+
|  Isolated Linux Container Environment (Docker / Podman)                         |
|  - Ubuntu 22.04 LTS, CUDA 12.4, Python 3.10                                     |
|  - PyTorch, JAX, PyRosetta 3, ProteinMPNN, AlphaFold2 Weights (~5.3 GB)         |
+---------------------------------------------------------------------------------+
```

---

## 4. Seven-Service Gap Analysis & Minimal Phase 2A Mapping

The Seven Services are **logical functional domains within a single Python codebase and SQLite database**, avoiding microservice sprawl:

| Service Domain | Base V1 Frozen Component | Current Baseline Gap | Phase 2A Minimal Required Mapping |
|---|---|---|---|
| **S1 Research Knowledge** | `schemas/evidence.py`<br>`schemas/decision.py`<br>`evidence/registry.py` | BindCraft primary papers, licenses, and decisions not formalized as records | Formalize Evidence Records (*Nature* 2025, DOI: 10.1038/s41586-025-09429-6) and Decision Records |
| **S2 Target & Data** | `schemas/target.py`<br>`schemas/common.py`<br>`storage/database.py` | No automated translation from `Target` schema to BindCraft PDB & hotspot CLI syntax | Specify conversion rules from `Target` (sequence, PDB structure, chains, hotspots) to BindCraft inputs |
| **S3 Generation** | `generators/base.py`<br>`schemas/candidate.py`<br>`core/pipeline.py` | `BindCraftGenerator` class does not exist in `src/` | Specify complete adapter class adhering strictly to `BaseGenerator` |
| **S4 Prediction & Evaluation** | `predictors/base.py`<br>`validation/base.py`<br>`configs/base.yaml` | BindCraft internal metrics need parsing; independent check must remain decoupled | Define native metric ingestion (pLDDT, i_pTM, dG) while enforcing independent validator separation |
| **S5 Diversity & Portfolio** | `diversity/clusters.py`<br>`schemas/candidate.py` | No sequence-hash deduplication across runs | Implement sequence-hash deduplication (`CandidateStatus.DUPLICATE`) and candidate family tagging |
| **S6 Experiment & Benchmark** | `schemas/experiment.py`<br>`core/pipeline.py`<br>`core/lifecycle.py` | No timeout, cancellation, or partial crash recovery for long-running GPU processes | Specify execution timeouts, SIGTERM/SIGKILL process management, and partial artifact retention |
| **S7 Evidence & Provenance** | `provenance/tracker.py`<br>`storage/artifacts.py`<br>`storage/database.py` | Checkpoint hashes, container digests, and command-line parameters not captured | Specify provenance schema capturing container digest, weights hash, seed, and config hash |

---

## 5. Licensing, IP & Compliance Governance

### 5.1 Multi-License Component Matrix

| Component | Upstream Origin | License Type | Commercial & Competition Policy | Operational Impact |
|---|---|---|---|---|
| **BindCraft Code** | Martin Pacesa et al. | MIT License | Permissive | Free to integrate via adapter code. |
| **BindCraft2 Code** | Pacesa Lab | Source-available, hosting-restricted | Restricted | Reference code only (not permissive MIT/Apache). |
| **AlphaFold2 Weights** | DeepMind / Google | CC-BY 4.0 | Permissive with attribution | Weights require standard attribution notice. |
| **ProteinMPNN** | Dauparas et al. | MIT License | Permissive | Fully open source. |
| **PyRosetta** | University of Washington (CoMotion / RosettaCommons) | Academic Non-Commercial | **NEEDS CASE-SPECIFIC CLEARANCE** | Free strictly for academic non-commercial research; competition use with corporate sponsors requires case-by-case legal review. |

### 5.2 Competition Participation & Legal Compliance Caveat
- **Critical Policy:** Participation in technological competitions (such as the Changjiang Cup 2026) **CANNOT automatically be presumed to satisfy the academic non-commercial PyRosetta license**. If the competition involves corporate sponsors, commercial co-organizers, commercial technology transfer, or commercial prize arrangements, explicit written legal clearance or a commercial PyRosetta license is required prior to deployment.
- **Unverified PyRosetta-Free Fallback:** Prior draft proposals suggested that a `--no-pyrosetta` flag could substitute OpenMM for all interface filtering. Investigation of upstream BindCraft source code confirms that PyRosetta FastRelax and interface scoring are deeply coupled into the default filtering pipeline. No verified OpenMM drop-in replacement exists upstream. Therefore, any "PyRosetta-free" mode is classified as **DEFERRED / UNVERIFIED IN UPSTREAM**.

---

## 6. Idempotency, Artifact Management & Runtime Integrity

### 6.1 Identity Separation
To prevent data corruption and race conditions, system identities are strictly decoupled:
1. **Request Identity (`request_id`):** Identifies the user or orchestrator intent (e.g. `req_20261013_001`). Must NEVER be derived from candidate sequences that have not yet been generated.
2. **Run Identity (`run_id`):** Identifies a specific execution attempt of the pipeline (`ExperimentRun.run_id`).
3. **Candidate Identity (`candidate_id`):** Unique, immutable identifier assigned to an ingested binder candidate (`cand_000001`).
4. **Sequence Hash (`sequence_hash`):** SHA-256 hash of the amino acid sequence used for canonical deduplication.

### 6.2 Seed Reproducibility vs Cache Hits
- **Cache Retrieval:** Reading previously persisted candidate records from SQLite based on identical target and config is an **idempotent cache hit**, NOT algorithmic reproduction.
- **Seed-Based Reproducibility:** Re-executing BindCraft with the same seed, target, and weights tests algorithmic determinism. Due to non-deterministic floating-point summation in CUDA/JAX GPU kernels, re-runs across different GPU architectures may yield slight coordinate divergence.

### 6.3 Genuine Structure Format Conversion (PDB to mmCIF)
- Base V1 storage layout mandates canonical mmCIF files (`binder.cif`, `complex.cif`) under `candidates/{target_id}/{candidate_id}/`.
- BindCraft natively produces `.pdb` structures in its `Accepted/` directory.
- **Mandate:** The adapter output parser MUST perform authentic structural translation using a recognized library (e.g., Gemmi or BioPython PDBx/mmCIF parser). **Simply renaming `.pdb` to `.cif` is strictly forbidden.**

### 6.4 Partial Artifact Retention & Crash Recovery
- If an execution fails, times out, or receives SIGINT/SIGTERM:
  1. The container supervisor issues `SIGTERM`, followed by `SIGKILL` after a 10-second grace period, guaranteeing no orphaned container processes.
  2. The parser scans the output workspace for any candidates that successfully completed full filtering prior to termination.
  3. Validly parsed candidates are persisted with status `GENERATED`.
  4. The `ExperimentRun` is marked `FAILED` or `PARTIAL`, attaching an `ErrorRecord` documenting the exit code, stderr tail, and failure stage.

---

## 7. Critical Scientific Warning: Real Generators with Dummy Validators

An essential systemic risk arises when integrating a real generator into a pipeline with placeholder validators:

```text
[Real BindCraft Generator] --> Produces Real Candidate
                                        │
                                        ▼
                           [DummyPredictor (Base V1)] --> Predicts Dummy Metrics
                                        │
                                        ▼
                           [DummyValidator (Base V1)] --> Always returns VALID
                                        │
                                        ▼
                     [Candidate Marked Status: VALID]
```

- **Warning:** In Phase 2B, when `BindCraftGenerator` is connected to the Base V1 pipeline, generated candidates will pass through `DummyValidator` and achieve status `VALID`.
- **System Policy & Provenance Gate:** A candidate marked `VALID` by `DummyValidator` **DOES NOT CONSTITUTE A SCIENTIFICALLY VALIDATED BINDER**. The candidate is strictly `COMPUTATIONALLY_GENERATED` under `docs/scientific_principles.md`. It must NEVER be presented to users or competition juries as functionally validated.
- **Publication Readiness Gate & Fail-Closed Guard:** Passing `DummyValidator` does NOT satisfy the Scientific Integrity Gate (`RESEARCH.md` §7, Principle I). The candidate's `publication_ready` attribute remains `False`. Phase 2B enforces a mandatory fail-closed export guard (`verify_export_safety(candidate, purpose)`) with strict purpose segregation:
  - `purpose = "competition"`: Verifies competition submission rules and candidate integrity; unconditionally blocks dummy-only validated candidates and corrupted artifacts, but does NOT mandate `publication_ready = True`.
  - `purpose = "publication"`: Mandates `publication_ready = True` and full 9-link provenance verification.

---

## 8. Four-Tier Testing Stratification (Tiers A-D)

```text
+--------------------------------------------------------------------------------+
|                           TESTING STRATIFICATION                               |
|                                                                                |
|  [Tier A] Fixture Parser Test  --> Static mock output parsing (NOT MEASURED)   |
|  [Tier B] Contract & Error QC  --> Exception isolation, timeout, mock runner   |
|  [Tier C] Runtime Environment  --> Container launch, volume mounts, GPU check  |
|  [Tier D] Real-Tool Smoke Test --> 1 minibinder generated with real AF2/MPNN   |
+--------------------------------------------------------------------------------+
```

1. **Tier A (Unit Parser):** Validates ingestion of static mock output fixtures (`tests/fixtures/bindcraft_output/`). Runs on CPU (latency: NOT MEASURED on host platform). Asserts parsing of native CSV column `Sequence` (NOT `mpnn_sequence`), normalized score metrics (`Average_pLDDT`, `Average_i_pTM`, `Average_i_pAE` on raw 0.0–1.0 scale), Rosetta interface energy (`Average_dG` in REU), and structural mmCIF conversion. Asserts schema parsing and numeric extraction accuracy; **does NOT assert biological quality thresholds**.
2. **Tier B (Contract Conformance & Export Safety):** Validates `BaseGenerator` inheritance, subprocess timeouts, non-zero exit codes, sequence-hash deduplication, and fail-closed export guard blocking dummy-validated candidates across both competition and publication export purposes.
3. **Tier C (Environment Pre-Flight):** Validates Docker daemon connectivity, volume mount permissions, and GPU passthrough availability.
4. **Tier D (Real-Tool End-to-End):** Executes authentic AF2 hallucination and ProteinMPNN sequence design producing 1 real minibinder on an authenticated Linux GPU instance.

---

## 9. Section D: Correction Log & Source Evidence Matrix

| Finding ID | Previous Erroneous Claim / Draft Text | Corrected Evidence-Grounded Text | File & Section | Primary Evidence Source | Status | Rationale for Open Status |
|---|---|---|---|---|---|---|
| **FINDING-C1-01** | Cited BindCraft as *Nature Biotechnology* (2024) | Corrected to *Nature* 646, 483–492 (2025). DOI: `10.1038/s41586-025-09429-6`. Title: *One-shot design of functional protein binders with BindCraft*. | `RESEARCH.md` §2, `READINESS.md` §2.1 | Pacesa et al., *Nature* 646 (2025) | **RESOLVED** | N/A |
| **FINDING-C1-02** | BindCraft2 conflated with published experimental affinities | Separated BindCraft2 as Level 6 unvalidated refactor; prohibited performance conflation | `RESEARCH.md` §2, `READINESS.md` §2.2 | PacesaLab/BindCraft2 GitHub repo | **RESOLVED** | N/A |
| **FINDING-C1-03** | Method decision recorded as final with arbitrary `Confidence: 0.90` | Decision categorized as **PROPOSED (Awaiting User Sign-Off)**; removed arbitrary confidence | `RESEARCH.md` §5 | `docs/scientific_principles.md` | **RESOLVED** | N/A |
| **FINDING-C2-01** | Upstream repository unpinned | Pinned full commit SHA `06e12a443a5796a798935c13b246a4825946fa7c` | `RESEARCH.md` §3.1, `SPECIFICATION.md` §3.1 | `martinpacesa/BindCraft` git log | **RESOLVED** | N/A |
| **FINDING-C3-01** | Assumed PDB files could be stored as CIF by changing file extension | Mandated structural conversion via Gemmi/BioPython parser | `SPECIFICATION.md` §3.5, `READINESS.md` §6.3 | Base V1 storage contract | **RESOLVED** | N/A |
| **FINDING-C4-01** | Predicted computational metrics conflated with binding affinity | Explicitly classified pLDDT, i_pTM, dG as computational predictions, not wet-lab Kd | `RESEARCH.md` §4, `SPECIFICATION.md` §3.5 | `docs/scientific_principles.md` | **RESOLVED** | N/A |
| **FINDING-C5-01** | Presumed competition participation satisfies academic PyRosetta license | Updated administrator to Univ. of Washington; flagged that sponsored competitions require case-specific clearance | `RESEARCH.md` §4.2 | Univ. of Washington CoMotion license | **RESOLVED** | N/A |
| **FINDING-C5-02** | Claimed `--no-pyrosetta` OpenMM fallback mode was ready | Marked `--no-pyrosetta` as **DEFERRED / UNVERIFIED IN UPSTREAM** | `RESEARCH.md` §3.3, `SPECIFICATION.md` §3.3 | BindCraft upstream source code | **RESOLVED** | N/A |
| **FINDING-C5-03** | Claimed 4GB VRAM GPU could support minibinders up to 60 AAs | Removed unsubstantiated VRAM commitments pending empirical benchmark measurements | `READINESS.md` §3.2 | Hardware profiling principles | **RESOLVED** | N/A |
| **FINDING-C7-01** | Equated database cache hit with seed-based algorithmic reproducibility | Decoupled cache hit from seed reproducibility on GPU hardware | `SPECIFICATION.md` §3.8, `READINESS.md` §6.2 | Determinism principles | **RESOLVED** | N/A |
| **FINDING-C8-01** | Parser unit tests hardcoded biological quality thresholds (pLDDT > 80) | Removed biological thresholds from parser tests; focused on schema & numeric accuracy | `TEST_PLAN_AND_HANDOFF.md` §1.1 | Unit testing principles | **RESOLVED** | N/A |
| **FINDING-C8-02** | Acceptance checklist marked items as [x] PASSED prior to implementation | Replaced with transparent statuses (`SPECIFICATION_COMPLETE`, `PENDING_IMPLEMENTATION`) | `TEST_PLAN_AND_HANDOFF.md` §3 | Quality governance | **RESOLVED** | N/A |
| **FINDING-C9-01** | Absence of formal scientific integrity and data ownership governance | Established Principles A through J, 9-link provenance chain, and `PUBLICATION_READY` gate | `RESEARCH.md` §7, `SPECIFICATION.md` §6 | Scientific integrity rules | **RESOLVED** | N/A |
| **FINDING-C10-01** | Simulated CLI arguments (`--pdb`, `--lengths`, `--seed`) not supported in upstream `bindcraft.py` | Corrected CLI interface to `--settings`, `--filters`, `--advanced`; mapped all parameters into JSON | `RESEARCH.md` §3.2, `SPECIFICATION.md` §3.3 | Upstream `bindcraft.py` argparse | **RESOLVED** | N/A |
| **FINDING-C11-01** | Assumed Base seed controls entire pipeline and claimed framework determinism | Cited upstream dynamic seed `np.random.randint`; documented Base seed does not control end-to-end without wrapper; removed determinism claims | `RESEARCH.md` §3.4, `SPECIFICATION.md` §3.8 | Upstream `bindcraft.py` source (line 91) | **RESOLVED** | N/A |
| **FINDING-C12-01** | Assumed native `Accepted/final_designs.fasta` and column name `mpnn_sequence` | Identified exact native column header `Sequence` (capitalized); recognized `mpnn_sequence` is Python variable only; FASTA made optional downstream | `RESEARCH.md` §3.3, `SPECIFICATION.md` §3.5 | Upstream `generic_utils.py` line 29 | **RESOLVED** | N/A |
| **FINDING-C13-01** | Conflated Rosetta $\Delta G$ with `ddG` and described REU as kcal/mol | Preserved exact native column `Average_dG` (REU); prohibited describing REU as kcal/mol | `RESEARCH.md` §3.3, `SPECIFICATION.md` §3.5 | Upstream `generic_utils.py` & `pyrosetta_utils.py` | **RESOLVED** | N/A |
| **FINDING-C14-01** | Misstated EGFR PDB `1NQL` resolution as 2.40 Å; misattributed BindCraft2 license | Corrected `1NQL` resolution to 2.80 Å (RCSB X-ray); classified full-length EGFR ectodomain as documented historical benchmark exception; corrected BindCraft2 license to source-available hosting-restricted | `RESEARCH.md` §1.2, §4.1, `TEST_PLAN_AND_HANDOFF.md` §2.3 | RCSB PDB structure `1NQL` & Pacesa Lab repo | **RESOLVED** | N/A |
| **FINDING-C15-01** | Used inaccurate target settings JSON keys (`"pdb"`, `"target_chains"`) | Established exact upstream keys: `"starting_pdb"`, `"chains"`, `"target_hotspot_residues"`, `"lengths"`, `"number_of_final_designs"`, `"binder_name"`, `"design_path"` | `SPECIFICATION.md` §3.3 | `settings_target/PDL1.json` & `bindcraft.py` | **RESOLVED** | N/A |
| **FINDING-C16-01** | Conflated native metric columns with informal aliases (`pLDDT`, `i_pTM`, `interface_dG`, `interface_sc`) | Established exact native CSV headers: `Average_pLDDT`, `Average_i_pTM`, `Average_i_pAE`, `Average_dG`, `Average_ShapeComplementarity`, `Average_PackStat`, etc. | `RESEARCH.md` §3.3, `SPECIFICATION.md` §3.5 | `functions/generic_utils.py` lines 16–38 | **RESOLVED** | N/A |
| **FINDING-C17-01** | Assumed pLDDT is 0–100 and pAE is in Ångströms natively | Identified native ColabDesign scales: pLDDT is 0.0–1.0 (float); pAE and i_pAE are normalized (0.0–1.0, dimensionless); separated raw upstream vs transformed Base V1 representation | `RESEARCH.md` §3.3, `SPECIFICATION.md` §3.5 | `colabdesign_utils.py` & `default_filters.json` | **RESOLVED** | N/A |
| **FINDING-C18-01** | Export safety guard forced `publication_ready = True` for all exports including competition | Separated `verify_export_safety(candidate, purpose)` into `competition` (eligibility rules, dummy-blocking) and `publication` (requires `publication_ready = True`) | `SPECIFICATION.md` §4.2, `READINESS.md` §7 | Scientific integrity protocols | **RESOLVED** | N/A |
| **FINDING-C19-01** | Missing comprehensive inventory of upstream rejected design data | Documented exact upstream rejected data assets: `failure_csv.csv`, `trajectory_stats.csv`, `mpnn_design_stats.csv`, `Trajectory/LowConfidence/`, `Trajectory/Clashing/`, `Rejected/` | `RESEARCH.md` §3.5, `SPECIFICATION.md` §3.6 | Upstream `bindcraft.py` line 427 & `generic_utils.py` | **RESOLVED** | N/A |
| **FINDING-C20-01** | Stale licensing administrator for PyRosetta (`Johns Hopkins University`) in readiness table | Updated official licensing administrator to University of Washington (CoMotion / RosettaCommons) | `READINESS.md` §5.1 | UW CoMotion license agreement | **RESOLVED** | N/A |

---

## 10. Conclusion & Next Steps

Phase 2A design correction has completed cross-document schema and factual reconciliation:
- All 20 findings (C1 through C20) are documented and verified against upstream source code (locked commit `06e12a443a5796a798935c13b246a4825946fa7c`) and literature evidence.
- The adapter specification conforms to frozen Base V1 contracts without modifying core engine interfaces.
- Implementation of `BindCraftGenerator`, unit test fixtures, and real GPU execution remain pending authorization and environment deployment (Phase 2B / Tier D).
- Phase 2B implementation will proceed only upon explicit User / Tech Lead authorization.

