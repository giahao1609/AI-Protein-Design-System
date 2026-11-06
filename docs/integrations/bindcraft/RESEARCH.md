# Deep-Dive Research & Comparative Analysis: BindCraft Integration

**System:** AI Protein Design System — Changjiang Cup 2026
**Document:** Model Research, Evidence Grounding & Upstream Analysis
**Phase:** Phase 2A — Source-Grounded Design Correction Round
**Target Branch:** `feature/bindcraft-integration`
**Status:** DRAFT PROPOSAL (Awaiting Review — Zero Breaking Changes)

---

## 1. Project Objectives & Scientific Principles

### 1.1 Dual-Track Objective: Competition & Scientific Publication
The AI Protein Design System is engineered from Day 1 with two co-equal primary deliverables:
1. **Competition Deliverable (Changjiang Cup 2026):** Generate a diverse, verified de novo binder library strictly complying with competition submission formats, sequence constraints, and epitope targeting guidelines.
2. **Scientific Publication Deliverable:** Conduct rigorous computational protein design research producing methodological contributions and empirical evidence of sufficient quality for submission to a peer-reviewed scientific journal.

**Core Scientific Axioms:**
- **Publication is Not Post-Competition Work:** Publication-grade rigor cannot be retrofitted post-hoc. Traceability, data splitting, baseline comparison, negative sample preservation, and provenance tracking must be active from the initial pipeline run.
- **Plumbing is Not Novelty:** Integrating multiple third-party tools (e.g. BindCraft, ProteinMPNN, PyRosetta, AlphaFold2) or wrapping them into 7 modular services constitutes **software engineering plumbing, not scientific novelty**. Novelty must arise from testable scientific hypotheses, robust evaluation methodologies, or empirical discovery.

Following the core principle **"AI Output Is Not Truth"** (`docs/scientific_principles.md`):
```text
CLAIM → EVIDENCE → INDEPENDENT CHECK → BENCHMARK → DECISION
```

---

### 1.2 Section A: Research Scope & Operational Bounds

#### Primary Research Questions (RQs):
- **RQ1 (Library Diversity vs. Greedy Selection):** Does systematic multi-objective portfolio selection (sampling diverse structural folds and distinct interface patches across an epitope) yield a higher wet-lab binding hit rate than greedy top-score selection (ranking solely by single-predictor pLDDT or ipTM)?
- **RQ2 (Computational Filter Fidelity & Generalization):** To what extent do composite in silico filter criteria ($\text{Average\_pLDDT} \ge 0.80$ [internal transformed scale: $\ge 80$], $\text{Average\_i\_pTM} \ge 0.80$, $\text{Average\_dG} \le -30\text{ REU}$, $S_c \ge 0.65$) correlate with true biophysical binding across diverse target surface topologies, and where do false-positive predictions concentrate?
- **RQ3 (Negative Sample Provenance in Iterative Design):** Does systematic retention and analysis of in silico failed/rejected trajectories (negative design space) improve sequence redesign efficiency and prevent degenerate sequence clustering across iterative design rounds?

#### Operational Scope & Target Boundaries:
- **Included Scope:**
  - Soluble globular protein targets with solved high-resolution 3D structures (X-ray crystallography $\le 2.5\text{ Å}$ or Cryo-EM $\le 3.0\text{ Å}$). For historical benchmarks inherited from the original BindCraft publication that possess lower resolution (specifically EGFR PDB `1IVO` at 3.30 Å and PDB `1NQL` at 2.80 Å; X-ray diffraction, Ferguson et al. *Mol Cell* 2003), the target is explicitly categorized as a documented historical benchmark exception to the strict $\le 2.5\text{ \AA}$ rule, because full-length glycosylated EGFR ectodomain assemblies intrinsically diffract between 2.8–3.3 Å. Rigorous $\le 2.5\text{ \AA}$ benchmarks are anchored to targets such as SARS-CoV-2 RBD (`6M0J`, 2.45 Å), PD-L1 (`4ZQK`, 2.20 Å), or truncated EGFR Domain I-III (`1MOX`, 2.50 Å).
  - De novo helical minibinders (length range: 40–120 amino acids).
  - Defined surface epitopes with identified or hypothesized hotspot residues.
- **Excluded / Out-of-Scope:**
  - Intrinsically disordered protein regions (IDPs) lacking stable conformational ensembles.
  - Transmembrane domains lacking lipid nanodisc / detergent micelle coordinates.
  - Multi-subunit complexes undergoing large allosteric conformational shifts upon binding.

#### Forbidden Scientific Conclusions (Without Experimental Proof):
Under strict enforcement of `docs/scientific_principles.md` and `docs/terminology.md`:
- **Strict Prohibition on Functional Claims:** Describing computational designs as *"functional"*, *"potent"*, *"high-affinity"*, *"strongly binding"*, or *"successful binders"* based solely on AI predictions is **STRICTLY FORBIDDEN**.
- **Prohibition on Metric Conflation:** Neither AlphaFold2 pLDDT/ipTM nor PyRosetta $\Delta G$ constitutes ground truth binding affinity. High scores indicate only internal geometric self-consistency within model parameters.
- **Strict Labeling:** Any computationally designed binder prior to wet-lab assay must strictly bear the scientific status label `COMPUTATIONALLY_GENERATED` or `COMPUTATIONALLY_VALIDATED` (if validated by an independent predictor). Only wet-lab assays (SPR, BLI, ITC, ELISA) justify the label `EXPERIMENTALLY_TESTED` or `EXPERIMENTALLY_VALIDATED`.

---

### 1.3 Section B: Prior Work & Contribution Matrix

| Category | Component / Tool | Upstream Origin / Prior Art | Project Usage / Distinction | Novelty & Claim Status |
|---|---|---|---|---|
| **Inherited Foundation** | **AlphaFold2 / Evoformer** | Jumper et al., *Nature* (2021) | Gradient backpropagation for backbone hallucination. | **Zero claim of novelty.** Reused as upstream computational engine. |
| **Inherited Foundation** | **ProteinMPNN** | Dauparas et al., *Science* (2022) | Fixed-backbone sequence generation. | **Zero claim of novelty.** Reused as upstream sequence designer. |
| **Inherited Foundation** | **PyRosetta / Rosetta scoring** | Chaudhury et al., *Bioinformatics* (2010); Alford et al. (2017) | Physics-based FastRelax, $\Delta G$, and interface shape complementarity. | **Zero claim of novelty.** Reused as upstream structural filter. |
| **Inherited Pipeline** | **BindCraft Pipeline** | Martin Pacesa et al., *Nature* 646, 483–492 (2025), DOI: `10.1038/s41586-025-09429-6`. Title: *One-shot design of functional protein binders with BindCraft*. | End-to-end hallucination-MPNN-Rosetta automated orchestration. | **Zero claim of novelty.** Pinned upstream reference implementation. |
| **Hypothesized Contribution** | **Multi-Objective Diversity Portfolio (S5)** | Proposed in this system | Clustering candidates across sequence space, structural fold, and interface patch to produce non-redundant library portfolios rather than standard upstream ranking. | **Hypothesis under investigation.** Evaluated across same pool and budget against upstream ranking, top-k, and random-k baselines. |
| **Hypothesized Contribution** | **Audit Trail & Negative Sample Retention (S6/S7)** | Proposed in this system | Uncorrupted tracking of in silico rejected trajectory counts (`rejection_counts`) and logs as ML research assets to study failure modes (no native `rejected_designs.csv` exists upstream). | **Engineering & empirical methodology contribution.** Subject to validation. |
| **Hypothesized Contribution** | **Decoupled Independent Validation (S4)** | Principle from `scientific_principles.md` | Strict separation where generator cannot validate itself; candidate evaluation requires independent orthogonal predictors (e.g. Chai-1/ESMFold). | **Methodological rigor contribution.** Prevents self-reinforcing model bias. |
| **Architectural Integration** | **Seven Logical Services (S1–S7)** | Base V1 Architecture | Separation of concerns across research knowledge, target data, generation, prediction, diversity, experiment, and provenance. | **Software plumbing only.** NOT a scientific novelty claim. |

#### Non-Claim Policy:
- The system **makes NO claim of guaranteed paper acceptance** or superiority over peer-reviewed baselines until formal benchmark data and experimental results are generated and peer-reviewed.
- Self-proclamation of "novelty" without experimental or mathematical justification is prohibited.

---


## 2. Comparative Analysis: BindCraft vs BindCraft2

Prior internal discussions and draft documentation proposed BindCraft2 as an engineering integration target alongside BindCraft. This section conducts a rigorous side-by-side comparison based on primary sources.

| Attribute | BindCraft (Original Pipeline) | BindCraft2 (Next-Gen Initiative) |
|---|---|---|
| **Primary Source / Origin** | Martin Pacesa et al., EPFL / Pacesa Lab.<br>Published in *Nature* 646, 483–492 (2025).<br>Title: *One-shot design of functional protein binders with BindCraft*. | Pacesa Lab GitHub repository.<br>`https://github.com/PacesaLab/BindCraft2` |
| **DOI / Permanent Identifier** | `10.1038/s41586-025-09429-6` | None (Active GitHub repository) |
| **Evidence Level** | **Level 3 (Peer-reviewed journal paper)** with extensive wet-lab validation (SPR, cryo-EM, binding kinetics). | **Level 6 (Model documentation / GitHub repo)**.<br>Active development/refactoring branch. |
| **Algorithmic Core** | AF2 Hallucination (backpropagation through AlphaFold2 loss) + ProteinMPNN sequence design + PyRosetta physics filtering + ColabFold/AF2 validation. | Streamlined modular pipeline, updated ColabFold integration, revised configuration format, optional ESMFold prediction modules. |
| **Upstream Code Reference** | `https://github.com/martinpacesa/BindCraft`<br>Locked Commit SHA: `06e12a443a5796a798935c13b246a4825946fa7c` | `https://github.com/PacesaLab/BindCraft2`<br>Unstable / subject to active breaking changes |
| **Input Specifications** | Target settings JSON (`--settings`), filters JSON (`--filters`), advanced settings JSON (`--advanced`). | Modular config JSON/YAML. |
| **Output Artifacts** | Binder PDB models (`Accepted/`, `Accepted/Ranked/`), summary CSV (`final_design_stats.csv`), trajectory logs. FASTA optional. | Similar outputs with updated score files and directory layout. |
| **Dependencies & Weights** | Linux (Ubuntu 20.04+), Python 3.10, CUDA 11.8/12.4, JAX, PyTorch, OpenMM, PyRosetta 3, AF2 weights (~5.3 GB), ProteinMPNN weights (~50 MB). | Linux, Python 3.10+, updated JAX/PyTorch stack, optional alternative predictors to reduce PyRosetta dependency. |
| **Licensing Matrix** | - Code: MIT (Open-Source)<br>- AF2 Weights: CC-BY 4.0<br>- ProteinMPNN: MIT<br>- PyRosetta: Univ. of Washington Academic Non-commercial (NEEDS CASE-SPECIFIC CLEARANCE for commercial/sponsored use). | - Code: Source-available, hosting-restricted license (not permissive open source MIT/Apache).<br>- PyRosetta: Same restriction or alternative backends under evaluation. |
| **Hardware & Runtime** | Dedicated Linux GPU instance (24 GB+ VRAM). High VRAM demands due to AF2 backpropagation. | Equivalent GPU compute demands due to shared AF2 backpropagation architecture. |
| **Empirical Status in This Repo** | Architecture analyzed; test fixture schemas conceptualized. **Zero empirical runs executed in this repo.** | Evaluated as future target. **Zero benchmarks or reproducible runs executed in this repo.** |

### 2.1 Critical Scientific Caveats
- **Prohibition on Performance Conflation:** The peer-reviewed wet-lab success rates, binding affinities (nanomolar/picomolar Kd), and design diversity reported by Pacesa et al. (*Nature* 2025) apply strictly to the validated **BindCraft** pipeline protocol. These performance attributes **CANNOT** be ascribed to BindCraft2 without independent empirical benchmarking.
- **Prohibition on "Reproduced" Claims:** Reading code repositories or verifying data parsers against static test fixtures does **NOT** constitute scientific reproduction. True reproduction requires end-to-end execution on verified benchmark targets producing experimentally or computationally comparable metrics.

---

## 3. Detailed Component Deep-Dive (BindCraft Original)

### 3.1 Algorithmic Stages & Source Workflow
1. **Target Preprocessing:**
   - Target structure parsed to isolate user-specified chains.
   - Hotspot residues identified and parameterized into AF2 loss functions to guide binder interface location.
2. **Backpropagation through AlphaFold2 (Hallucination):**
   - Seed binder sequence is optimized using gradient descent through AF2's Evoformer and structure module.
   - Loss function combines binder self-folding pLDDT, complex pLDDT, interface contact loss, and target hotspot interaction rewards.
   - Initialized via dynamically sampled trajectory PRNG seed within the main execution loop (`seed = int(np.random.randint(0, high=999999, size=1, dtype=int)[0])` in `bindcraft.py:91`).
3. **Sequence Redesign with ProteinMPNN:**
   - The hallucinated backbone is fixed.
   - ProteinMPNN redesigns residues on the binder backbone to maximize sequence compatibility, stability, and target surface complementarity.
   - Parameterized by the current trajectory seed passed to the sequence generator.
4. **Physics-Based QC with PyRosetta:**
   - FastRelax and interface scoring calculate binding energy (`Average_dG`), buried surface area (`Average_dSASA`), shape complementarity (`Average_ShapeComplementarity`), and steric clashes.
5. **AF2/ColabFold Internal Validation:**
   - Designed sequences are refolded independently without template assistance across 5 AF2 models to verify folding fidelity and interface stability (`Average_pLDDT`, `Average_i_pTM`, `Average_i_pAE`).

### 3.2 Upstream CLI Arguments & Configuration
In upstream BindCraft (commit `06e12a443a5796a798935c13b246a4825946fa7c`), the execution script `bindcraft.py` is invoked strictly with:
```bash
python -u ./bindcraft.py \
  --settings <target_settings.json> \
  --filters <filters.json> \
  --advanced <advanced.json>
```
**Argument Mapping Rule:**
- `--settings` / `-s` (required): Path to the target settings JSON file.
- `--filters` / `-f` (optional, default: `./settings_filters/default_filters.json`): Path to filter parameters JSON.
- `--advanced` / `-a` (optional, default: `./settings_advanced/default_4stage_multimer.json`): Path to advanced settings JSON.
- **Verification Rule:** Upstream argparse contains **NO** `--pdb`, `--target_chains`, `--hotspot`, `--lengths`, `--number_of_designs`, or `--seed` CLI arguments. All design parameters (target PDB path, target chains, hotspot residue identifiers, binder length bounds, and requested final design count) are serialized inside the `--settings` JSON file by the adapter before execution.

### 3.3 Native Output Inventory & Exact CSV Dictionary
BindCraft organizes output in the designated run directory (`design_path`):
- `Trajectory/`: Intermediate PDB trajectory snapshots recorded during AF2 hallucination steps.
- `Trajectory/LowConfidence/` & `Trajectory/Clashing/`: Intermediate trajectories failing confidence or clash checks.
- `Accepted/`: PDB models of target-binder complexes passing all internal loss and filter thresholds. Once the requested design quota is met, top-performing complexes sorted by `Average_i_pTM` are placed in `Accepted/Ranked/`.
- `Rejected/`: Candidate-level PDB models of ProteinMPNN redesigns that failed downstream filters (copied via `shutil.copy`).
- `trajectory_stats.csv`: Trajectory tracking stats across attempted hallucination iterations.
- `mpnn_design_stats.csv`: Intermediate metrics from ProteinMPNN redesign rounds across all candidate attempts.
- `failure_csv.csv`: Aggregate rejection counters logging each filter failure event.
- `final_design_stats.csv`: Canonical summary table containing final structural, AF2-multimer, and PyRosetta evaluation metrics.
- **Sequence Source-of-Truth:** Upstream does **NOT** produce an `Accepted/final_designs.fasta` file. The canonical source-of-truth for candidate sequences is the **`Sequence`** column in `final_design_stats.csv` (or extracted directly from atomic coordinates in `Accepted/*.pdb`). Note that `mpnn_sequence` is strictly an internal Python loop variable name (`mpnn_sequence['seq']` in `bindcraft.py`), NOT a native CSV column header. Downstream FASTA file generation by the adapter is strictly an **optional convenience artifact**.

#### Exact Native Column Dictionary vs Internal Base V1 Ingestion:

Generated by `generate_dataframe_labels()` in `functions/generic_utils.py:16–38`:

| Native CSV Column | Producing Tool / Stage | Raw Scale & Format | Physical Meaning / Unit | Base V1 Target Mapping | Aggregation Semantics | Missing-Value Policy |
|---|---|---|---|---|---|---|
| `Design` | Orchestrator (`bindcraft.py`) | String (`PDL1_binder_...`) | Design candidate identifier | `candidate.metadata["upstream_design_id"]` | Primary Key per design | Mandatory |
| `Sequence` | ProteinMPNN (`functions/colabdesign_utils.py`) | String (e.g. `MKT...`) | Designed binder amino acid sequence (**Canonical Source of Truth**) | `candidate.sequence` | Sequence of accepted candidate | Mandatory (Drop if missing) |
| `Length` | Design configuration | Integer (e.g. `65`) | Binder length in amino acids | `candidate.metadata["binder_length"]` | Single value | Mandatory |
| `Seed` | PRNG (`np.random.randint`) | Integer (0–999999) | Trajectory random seed recorded by upstream | `candidate.metadata["upstream_seed"]` | Single trajectory seed | Mandatory |
| `Average_pLDDT` | ColabDesign / AF2 | **0.0–1.0 float** (rounded to 2 decimals, threshold `0.80`) | Mean predicted local distance difference test across AF2 models | `candidate.metrics["af2_plddt"]` (raw 0.0–1.0; transformed 0–100 requires explicit conversion) | Mean across 5 AF2 prediction models | Recorded as null if unpredicted |
| `Average_pTM` | ColabDesign / AF2 | 0.0–1.0 float | Complex predicted TM-score | `candidate.metrics["af2_ptm"]` | Mean across 5 AF2 prediction models | Recorded as null if unpredicted |
| `Average_i_pTM` | ColabDesign / AF2 | 0.0–1.0 float (threshold `0.80`) | Interface predicted TM-score | `candidate.metrics["af2_iptm"]` | Mean across 5 AF2 prediction models (used for `Accepted/Ranked/` sorting) | Recorded as null if unpredicted |
| `Average_pAE` | ColabDesign / AF2 | **0.0–1.0 float** (normalized by dividing raw PAE by 31.0, threshold `0.35`) | Mean normalized predicted aligned error across complex (**NOT Ångströms**) | `candidate.metrics["af2_pae"]` | Mean across 5 AF2 prediction models | Recorded as null if unpredicted |
| `Average_i_pAE` | ColabDesign / AF2 | **0.0–1.0 float** (normalized by dividing raw interface PAE by 31.0, threshold `0.35`) | Interface predicted aligned error (**NOT Ångströms**) | `candidate.metrics["af2_interface_pae"]` | Mean across 5 AF2 prediction models | Recorded as null if unpredicted |
| `Average_i_pLDDT` | ColabDesign / AF2 | **0.0–1.0 float** | Interface residue predicted local distance difference test | `candidate.metrics["af2_interface_plddt"]` | Mean across 5 AF2 prediction models | Recorded as null if unpredicted |
| `Average_ss_pLDDT` | ColabDesign / AF2 | **0.0–1.0 float** | Secondary structure element pLDDT | `candidate.metrics["af2_ss_plddt"]` | Mean across 5 AF2 prediction models | Recorded as null if unpredicted |
| `Average_Unrelaxed_Clashes` | PyRosetta / BioPython | Integer count | Inter-chain heavy atom steric clash count before FastRelax | `candidate.metrics["unrelaxed_clashes"]` | Mean across models | 0 if missing |
| `Average_Relaxed_Clashes` | PyRosetta | Integer count | Inter-chain heavy atom steric clash count after FastRelax | `candidate.metrics["relaxed_clashes"]` | Mean across models | 0 if missing |
| `Average_Binder_Energy_Score` | PyRosetta ScoreFunction | REU (Rosetta Energy Units) | Normalized binder internal folding energy | `candidate.metrics["binder_energy_score"]` | Mean across models | Recorded as null if unrelaxed |
| `Average_Surface_Hydrophobicity` | PyRosetta / BioPython | Float (fraction 0.0–1.0) | Fraction of exposed hydrophobic surface residues | `candidate.metrics["surface_hydrophobicity"]` | Mean across models | Recorded as null if uncalculated |
| `Average_ShapeComplementarity` | PyRosetta Sc / DAlphaBall | 0.0–1.0 float (Lawrence & Colman $S_c$) | Interface shape complementarity | `candidate.metrics["pyrosetta_interface_sc"]` | Mean across models | Recorded as null if Sc fails |
| `Average_PackStat` | PyRosetta PackStat | 0.0–1.0 float | Interface atomic packing efficiency statistic | `candidate.metrics["pyrosetta_interface_packstat"]` | Mean across models | Recorded as null if uncalculated |
| `Average_dG` | PyRosetta InterfaceAnalyzer | **REU (Rosetta Energy Units)** (empirical statistical potential, **NEVER kcal/mol, NEVER renamed to ddG**) | Interface binding energy estimate | `candidate.metrics["pyrosetta_interface_dg"]` | Mean across models | Recorded as null if unrelaxed |
| `Average_dSASA` | PyRosetta InterfaceAnalyzer | **$\text{Å}^2$** (square Ångströms) | Buried solvent-accessible surface area | `candidate.metrics["pyrosetta_interface_dsasa"]` | Mean across models | Recorded as null if unrelaxed |
| `Average_dG/dSASA` | PyRosetta InterfaceAnalyzer | $\text{REU} / \text{Å}^2$ | Binding energy density per unit buried surface | `candidate.metrics["pyrosetta_dg_dsasa"]` | Mean across models | Recorded as null if unrelaxed |
| `Average_Interface_SASA_%` | PyRosetta InterfaceAnalyzer | Percentage (0.0–100.0%) | Fraction of binder total surface area buried in interface | `candidate.metrics["interface_sasa_pct"]` | Mean across models | Recorded as null if unrelaxed |
| `Average_Hotspot_RMSD` | BioPython Superimposer | Å (Ångströms) | Hotspot residue backbone RMSD to initial target coordinates | `candidate.metrics["hotspot_rmsd"]` | Mean across models | Recorded as null if no hotspots |
| `Average_Target_RMSD` | BioPython Superimposer | Å (Ångströms) | Target structure backbone RMSD to initial target coordinates | `candidate.metrics["target_rmsd"]` | Mean across models | Recorded as null if unaligned |
| `Average_Binder_RMSD` | BioPython Superimposer | Å (Ångströms) | Binder backbone RMSD across prediction models | `candidate.metrics["binder_rmsd"]` | Mean across models | Recorded as null if unaligned |
| `{1..5}_<label>` | ColabDesign / PyRosetta | Corresponding label scale | Individual AF2 model prediction metrics (e.g. `1_pLDDT`, `2_i_pTM`, `1_dG`) | `candidate.metadata["model_metrics"][model_num][label]` | Single model metric | Recorded per model |

*Note on Raw vs Transformed Scales:* In raw upstream ColabDesign output, pLDDT, pTM, i_pTM, pAE, and i_pAE are all bounded in [0.0, 1.0]. If the internal Base V1 system wishes to expose pLDDT on a 0–100 scale, this must be an explicit, versioned transformation (`transformed_plddt = raw_plddt * 100.0`) while preserving the raw value verbatim under `candidate.metrics["raw_af2_plddt"]`.

### 3.4 Seed Mechanism & Floating-Point Determinism Limits
- **Upstream Seed Source Citation:** Inspection of `bindcraft.py` at pinned commit `06e12a443a5796a798935c13b246a4825946fa7c` confirms that random seeds are sampled dynamically inside the main trajectory loop:
  ```python
  seed = int(np.random.randint(0, high=999999, size=1, dtype=int)[0])
  ```
- **Disentangling Five Seed & Reproducibility Concepts:**
  1. **Base API Seed (`BaseGenerator.generate(..., seed)`):** The seed parameter specified in the pipeline configuration or Base V1 contract. Because upstream `bindcraft.py` exposes NO `--seed` flag, passing this seed to the adapter does NOT control upstream pipeline trajectories end-to-end without explicit wrapper intervention (e.g. setting `PYTHONHASHSEED`, calling `np.random.seed(seed)` in an execution wrapper, or modifying target settings).
  2. **Upstream Internal Trajectory Seed:** The dynamic integer sampled by `bindcraft.py:91` for each attempted design trajectory and recorded in `final_design_stats.csv` under column `Seed`.
  3. **Wrapper-Controlled Seed:** Interventions applied by the adapter layer (e.g. environment variable overrides, pre-seeding PRNG before script launch, or injecting deterministic settings) to enforce reproducibly seeded sequences.
  4. **Algorithmic Reproducibility vs Bitwise Determinism:** Re-running generation with an identical trajectory seed tests algorithmic reproducibility within floating-point tolerance. On modern GPU architectures (Ampere, Ada, Hopper), non-deterministic atomic reduction order in cuDNN and JAX kernels means bit-for-bit identical coordinates are not guaranteed. No claim of framework bitwise determinism is made.
  5. **Cache Hit:** Re-reading an existing candidate from the SQLite database based on matching target and configuration hash is an **idempotent cache hit**, NOT an algorithmic reproduction test.

### 3.5 Rejected Data Inventory & Trajectory Accounting
Upstream BindCraft generates rich negative design data during filtering:
1. **Aggregate Rejection Counters (`failure_csv.csv` & stdout):** Logs cumulative counts of trajectories discarded at each filter step (`Trajectory`, `Length`, `pLDDT`, `Contact_Loss`, `Clash`, `Rosetta_dG`, etc.). Ingested by the adapter into `ExperimentRun.output_summary["rejection_counts"]`.
2. **Trajectory-Level Metadata (`trajectory_stats.csv`):** Captures loss convergence, intermediate pLDDT, contact loss, and filter evaluation across all hallucination iterations.
3. **Candidate-Level Rejected Artifacts (`Rejected/*.pdb` & `mpnn_design_stats.csv`):** Candidate PDB files of ProteinMPNN redesigns that failed downstream filters are preserved directly in `output/Rejected/` via `shutil.copy(best_model_pdb, design_paths["Rejected"])` in `bindcraft.py:427`. Metrics for all attempted MPNN redesigns are recorded in `mpnn_design_stats.csv`. These candidate-level rejected artifacts represent valuable empirical assets for negative design space ML research.
4. **Trajectory Rejection PDBs (`Trajectory/LowConfidence/` & `Trajectory/Clashing/`):** PDB coordinates from intermediate hallucination steps discarded due to low backbone confidence or severe atomic steric clashes.
5. **Accepted Candidate Artifacts (`Accepted/*.pdb`, `Accepted/Ranked/*.pdb`, `final_design_stats.csv`):** PDB complexes passing all filters, from which canonical candidate records are ingested into the database.
6. **Unavailable / Unobservable Failures:** Early numerical instabilities (e.g. gradient explosion or loss divergence before coordinates are written to disk) cannot be reconstructed as 3D structures and are observable only via stderr execution logs.

**Strict Rejection Accounting Policy:** The adapter **MUST NOT** fabricate phantom candidate records (`cand_000001`...) in the `Candidate` table for unaccepted trajectories, nor invent a non-existent `rejected_designs.csv` file. Rejections are preserved through trajectory counters on `ExperimentRun` and by indexing candidate-level structures in `Rejected/*.pdb` within the research negative dataset partition.

---

## 4. Licensing, IP & Compliance Governance

### 4.1 Multi-License Component Matrix

| Component | Upstream Origin | License Type | Commercial & Competition Policy | Operational Impact |
|---|---|---|---|---|
| **BindCraft Code** | Martin Pacesa et al. | MIT License | Permissive | Free to use and integrate via adapter code. |
| **BindCraft2 Code** | Pacesa Lab | Source-available, hosting-restricted | Restricted | Reference code only (not permissive MIT/Apache). |
| **AlphaFold2 Weights** | DeepMind / Google | CC-BY 4.0 | Permissive with attribution | Weights require standard attribution notice. |
| **ProteinMPNN** | Dauparas et al. | MIT License | Permissive | Fully open source. |
| **PyRosetta** | University of Washington (CoMotion / RosettaCommons) | Academic Non-Commercial | **NEEDS CASE-SPECIFIC CLEARANCE** | Free strictly for academic non-commercial research; competition use with corporate sponsors requires case-by-case legal review. |

### 4.2 Competition Participation & Legal Compliance
- **Legal Review Requirement:** Participation in technological competitions (such as the Changjiang Cup 2026) **CANNOT automatically be presumed to satisfy the academic non-commercial PyRosetta license**. If the competition involves corporate sponsors, commercial co-organizers, commercial technology transfer, or commercial prize arrangements, the project **NEEDS CASE-SPECIFIC CLEARANCE** from University of Washington CoMotion / RosettaCommons rather than making preemptive legal assumptions.
- **PyRosetta-Free Mode Status:** Prior draft documents suggested that a `--no-pyrosetta` flag could substitute OpenMM for all interface filtering. Investigation of upstream BindCraft source code confirms that PyRosetta FastRelax and interface scoring are deeply coupled into the default filtering pipeline. No verified OpenMM drop-in replacement exists upstream. Therefore, any "PyRosetta-free" mode is classified as **DEFERRED / UNVERIFIED IN UPSTREAM**.

### 4.3 Section E: Competition Publication Conditions & IP Clearance Checklist

To ensure that participation in the Changjiang Cup 2026 does not compromise the publication of scientific research, the following rights, data access, and legal conditions must be formally verified with the competition organizers. All items currently unverified are recorded with status **OPEN**:

| Item ID | Governance Dimension | Specific Clarification Needed from Organizers | Status | Operational Impact on Research |
|---|---|---|---|---|
| **COMP-PUB-01** | **Sequence & Structure IP Ownership** | Do competition organizers or sponsors claim proprietary or commercial ownership over candidate sequences/structures submitted by participants? | **OPEN** | If organizers claim exclusive rights, public journal preprint/paper submission may require explicit legal release. |
| **COMP-PUB-02** | **Experimental Wet-Lab Data Access** | Will participants receive raw biophysical measurement data (e.g. SPR sensorgrams, BLI binding curves, ELISA OD values, expression yields, purity SDS-PAGE) for submitted candidates? | **OPEN** | Publication requires access to raw experimental curves, error bars, and replicates, not merely competition ranking points. |
| **COMP-PUB-03** | **Publication Embargo Period** | Is there a mandatory confidentiality embargo or non-disclosure blackout period prior to the official announcement of competition winners? | **OPEN** | Preprint submission (bioRxiv/arXiv) must be scheduled strictly in accordance with embargo termination. |
| **COMP-PUB-04** | **Attribution & Acknowledgments** | What are the mandatory attribution guidelines for citing competition organizers, sponsors, or experimental testing facilities in scientific publications? | **OPEN** | Manuscript draft must include approved acknowledgment and funding statements. |
| **COMP-PUB-05** | **PyRosetta Commercial Clearance** | Do competition prize arrangements, corporate sponsorships, or industry partner evaluations trigger the commercial licensing clause of the PyRosetta Academic License? | **OPEN** | If commercial sponsors are involved, explicit case-specific clearance from University of Washington (CoMotion / RosettaCommons) is required. |
| **COMP-PUB-06** | **Negative Sample Publication Rights** | Are participants free to publish analyses of candidates that were rejected or failed experimental validation during the competition? | **OPEN** | Critical for scientific publication: failure mode analysis is a major research deliverable. |

---


## 5. Hardware Reality & Risk Mitigations

### 5.1 Environment Classification
- **Development Host (macOS Apple Silicon):** Development, core pipeline, SQLite store, mock fixture parsing (Tier A/B). Native CUDA execution impossible.
- **Secondary Local Node (Windows WSL2 RTX 3050 4GB VRAM):** Severely VRAM-constrained. Zero empirical benchmarks executed.
- **Target Production Runtime:** Dedicated Linux Instance (NVIDIA A100 / RTX 4090 / L40S, 24 GB+ VRAM).
- **Executed Runtime to Date:** **None (Zero real GPU runs in this repository).**

### 5.2 Removal of Unsubstantiated Commitments
- Prior claims asserting that 4 GB VRAM supports minibinders up to 60 amino acids are **removed**. VRAM consumption depends on target sequence length, crop size, recycling iterations, and Evoformer activation memory. No empirical profiling has been conducted on local hardware; therefore, no VRAM-versus-length commitments are made without empirical benchmark data.

---

## 6. Proposed Method Decision (Awaiting User Sign-Off)

### 6.1 Decision Proposal (PROPOSED)
- **Question:** Which BindCraft variant should be adopted as the formal baseline target for Phase 2 adapter implementation?
- **Proposed Selection:** **BindCraft Original (Locked Commit `06e12a443a5796a798935c13b246a4825946fa7c`)** is proposed as the primary target for Phase 2 implementation. BindCraft2 is categorized as a deferred experimental backend.
- **Status:** **PROPOSED (Awaiting User Sign-Off)**.
- **Evidence Grounding:** Supported by peer-reviewed experimental literature (*Nature* 646, 483–492 (2025), DOI: `10.1038/s41586-025-09429-6`, Level 3 Evidence) and verified open-source repository. Arbitrary numerical confidence scores have been eliminated in accordance with `docs/scientific_principles.md`.

### 6.2 Supporting Rationale
1. **Literature Evidence:** BindCraft original has published wet-lab validation data across diverse targets (e.g., SARS-CoV-2 RBD, EGFR, PD-L1).
2. **Stable Workflow:** Command-line parameters, output schemas, and file hierarchies are stabilized and documented.
3. **Pluggable Architecture:** By defining a clean adapter interface (`BindCraftGenerator`) adhering to `BaseGenerator`, evaluating BindCraft2 or RFdiffusion in subsequent phases will require zero changes to core pipeline orchestration.

---

## 7. Hard Principles: Scientific Integrity, Data Ownership & Evidence Governance

The AI Protein Design System operates simultaneously towards two complementary objectives:
1. **Competition Track:** Producing a high-diversity, rule-compliant binder library for the Changjiang Cup 2026.
2. **Research Track:** Delivering rigorous, publication-grade scientific contributions suitable for peer-reviewed dissemination.

To guarantee that competitive ambition never compromises scientific credibility, all research results, computational artifacts, and experimental data within this system must strictly adhere to ten mandatory hard principles:

### Principle A: No Fabricated Data
- Generating, extrapolating, inventing, or filling in numerical data, affinity metrics ($K_d$, $\text{IC}_{50}$), or structural scores not produced by a verifiable, traceable source is strictly prohibited.
- Placeholder, simulated, or dummy values must be explicitly named and restricted to pipeline integration tests (`Tier A/B`); they must never be presented as empirical results or evaluation metrics.

### Principle B: No Result Misattribution
- Metrics, success rates, structural resolutions, and binding affinities reported in external publications, preprints, or upstream author repositories constitute strictly **EXTERNAL/LITERATURE EVIDENCE**.
- Under no circumstances may published external achievements (e.g. picomolar affinities reported in Pacesa et al., *Nature* 2025) be presented, claimed, or implied as achievements or capabilities of the AI Protein Design System.

### Principle C: Self-Generated Project Results & Nine-Link Provenance
- Every metric, figure, table entry, or performance claim designated as "our result" must be strictly generated by our own project runs adhering to a formal, logged protocol.
- Every self-generated data point must be 100% auditable through the complete **Nine-Link Provenance Chain**:
  ```text
  [Target Revision] ──> [Source] ──> [Experiment Run] ──> [Config Hash] ──> [Code Commit]
                                                                                  │
  [Analysis Script] <── [Raw Artifact] <── [PRNG Seed] <── [Model/Weights Identity] ┘
  ```
  1. **Target Revision:** Exact target sequence, crystal structure PDB ID/chain, or epitope definition.
  2. **Source:** Origin of input files, structural cleaning steps, and preprocessing logs.
  3. **Experiment Run:** Unique `run_id` registered in the SQLite metadata store.
  4. **Config Hash:** Cryptographic SHA-256 hash of all runtime hyperparameters and arguments.
  5. **Code Commit:** Git commit SHA of the repository executing the generation.
  6. **Model/Weights Identity:** Checksum and identity of neural network weights (e.g. AF2 params, ProteinMPNN model).
  7. **PRNG Seed:** Initial random seed recorded for algorithmic reproducibility verification.
  8. **Raw Artifact:** Unmodified raw output files (PDB/CIF, score CSV, execution logs; FASTA optional).
  9. **Analysis Script:** Versioned script producing summary statistics, tables, or plots.

### Principle D: Experimental Attribution & Biophysical Rigor
- If wet-lab validation (SPR, BLI, ELISA, cell binding assays, crystallization) is conducted by Changjiang Cup organizers, host facilities, or collaborative partners, the executing entity must be explicitly and prominently credited.
- The project team must never state or imply that wet-lab experiments were conducted in-house if performed by third parties.
- Inferring binding constants ($K_d$), affinity ranges, or quantitative thermodynamics from competition leaderboard rankings, scoring placements, or binary qualification outcomes is strictly prohibited.

### Principle E: Failure Retention & Six-Category Failure Taxonomy
- Negative outcomes, discarded trajectories, and experimental failures must never be purged, hidden, or suppressed to artificially inflate success rates.
- Failures must be systematically recorded under a strict **Six-Category Failure Taxonomy**:
  1. `computational_rejection`: Trajectories discarded during in silico generation by geometric, clash, or score filters.
  2. `execution_failure`: Process crashes, CUDA OOM, timeouts, container exit codes, or unhandled exceptions.
  3. `untested`: Candidates generated and ranked computationally that have not been physically synthesized or assayed.
  4. `assay_negative`: Synthesized candidates experimentally confirmed in wet-lab assays to exhibit no measurable binding.
  5. `assay_inconclusive`: Assays yielding ambiguous signals, high non-specific background, or measurement artifacts.
  6. `expression_qc_failure`: Candidates failing wet-lab protein expression, solubility, or biochemical QC purity checks.
- **Critical Scientific Boundary:** A `computational_rejection` is strictly an in silico filter event and **MUST NOT** be claimed or labeled as a biological negative without physical assay validation.

### Principle F: Competition / Research Track Separation
- **Competition Track:** Retains operational freedom to continuously optimize candidate portfolios, adjust selection heuristics, and scale library diversity to maximize competition performance.
- **Research Track:** Requires a formal protocol freeze prior to evaluating benchmark sets or ablation conditions.
- **Anti-Leakage Prohibition:** Competition feedback, leaderboard rankings, or jury annotations utilized to adjust design methods or hyperparameters **CANNOT** be recycled or reported as untouched, held-out test evidence in research publications.

### Principle G: Public Data Governance & Licensing Verification
- Every external dataset, structural repository, and pre-trained model checkpoint incorporated into the system must record:
  - Source origin (URL / repository)
  - Version identifier
  - License type
  - Cryptographic checksum (SHA-256)
  - Retrieval date
  - Allowed-use status (Academic, Commercial, Competition-cleared)
  - Formal academic citation
- Data assets or checkpoints with `UNKNOWN` license or unverified usage rights are strictly prohibited from being silently introduced into model training, fine-tuning, or production workflows.

### Principle H: Publication Numbers & Scripted Pipeline
- Numerical values in scientific tables, manuscripts, and reports must never be manually copy-pasted or transcribed.
- All result tables, summary statistics, and visualization figures must be generated programmatically from raw project artifacts via versioned analysis scripts (`scripts/analysis/`).

### Principle I: Scientific Integrity & Provenance Gate
- A candidate or experiment result achieves status `PUBLICATION_READY` if and only if all mandatory provenance criteria are verified:
  1. Source provenance documented
  2. Allowed usage rights and license cleared
  3. Repository code commit SHA recorded
  4. Model checkpoint and weights identity verified
  5. Complete execution configuration logged
  6. PRNG seed recorded (where applicable)
  7. Raw artifact files persisted and intact
  8. Analysis procedure and script version identified
  9. Explicit claim type declared (computational prediction vs empirical measurement)
  10. Commensurate evidence level according to the hierarchy.
- **Integrity Rule:** If ANY mandatory evidence element is missing or unverified, the gate evaluation automatically evaluates:
  ```text
  PUBLICATION_READY = False
  ```
- **Base V1 Non-Invasive Mapping:** In accordance with the Base V1 freeze, this gate does not modify the frozen `CandidateStatus` lifecycle enum. It is enforced as an evidence metadata attribute (`provenance.publication_ready`) in the candidate's `ProvenanceRecord`.

### Principle J: External Baselines Taxonomy
- External baselines must be categorized under a strict **Four-Tier Verification Taxonomy**:
  1. `LITERATURE_REPORTED`: Metrics quoted directly from external publications (Literature context only).
  2. `SOURCE_VERIFIED`: Metrics verified by inspecting author code, raw repositories, or supplementary materials.
  3. `LOCALLY_REPRODUCED`: Baseline executed locally using third-party upstream code and parameters.
  4. `PROJECT_BENCHMARKED`: Baseline executed directly within our project framework on identical targets, identical evaluation metrics, and identical hardware protocols.
- **Baseline Benchmark Rule:** Only `PROJECT_BENCHMARKED` results may be cited as baseline performance of experiments conducted by the project. External published numbers must never be substituted as locally run baseline performance.

### Dual Mission Safeguard
- The library-generation mandate for the Changjiang Cup 2026 remains a core mission: producing a large, diverse binder library must proceed vigorously.
- Publication integrity protocols govern scientific attribution and evidence reporting; they do not restrict the candidate exploration space of the Competition Track.

---

## 8. Section D: Correction Log & Source Evidence Matrix

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


