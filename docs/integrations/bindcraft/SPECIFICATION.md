# BindCraft Adapter & Seven-Service Mapping Specification

**System:** AI Protein Design System — Changjiang Cup 2026
**Document:** Adapter Architectural Specification & Seven-Service Mapping
**Phase:** Phase 2A — Source-Grounded Design Correction Round
**Target Branch:** `feature/bindcraft-integration`
**Status:** DRAFT SPECIFICATION (Awaiting Review — Zero Breaking Changes)

---

## 1. Architectural Guardrails & Principles

To prevent architectural drift and maintain system simplicity:
1. **No Microservice Overhead:** The Seven Services are **logical functional domains within a unified Python package and SQLite storage system**. There will be **no** separate HTTP microservices, **no** seven independent databases, and **no** separate git repositories.
2. **Reuse Existing Base V1 Infrastructure:** The existing frozen metadata database (`MetadataStore`), artifact store (`ArtifactStore`), lifecycle state machine (`lifecycle.py`), and pipeline coordinator (`Pipeline`) are strictly reused without duplication.
3. **Strict Adapter Decoupling:** Model-specific logic lives entirely inside adapter implementations (`src/protein_design/generators/bindcraft.py`). The core orchestration engine remains model-agnostic.
4. **Lifecycle Authority Isolation:** The generator adapter **only** produces candidates in initial status `CandidateStatus.GENERATED`. It **never** self-promotes candidates to `VALID`.

---

## 2. Minimal Seven-Service Mapping for Phase 2A/2B

```text
+---------------------------------------------------------------------------------------+
|                              7-SERVICE LOGICAL DOMAIN MAP                             |
|                                                                                       |
|  [S1 Research Knowledge]   --> Evidence & Decision Records (*Nature* 2025, Licenses)  |
|  [S2 Target & Data]        --> Target PDB extraction, Chain/Hotspot Parameterization  |
|  [S3 Generation]           --> BindCraftGenerator Adapter (Subprocess/Docker Runner)  |
|  [S4 Prediction & Eval]    --> Parse Internal Metrics + Decouple Independent Check    |
|  [S5 Diversity & Port]     --> Sequence Hash Deduplication + Cluster Metadata Tagging |
|  [S6 Experiment & Bench]   --> Run Lifecycle, Timeout Control, Checkpoint Resume      |
|  [S7 Evidence & Provenance]--> Artifact Store, ProvenanceRecord, Weights Hashing      |
+---------------------------------------------------------------------------------------+
```

### 2.1 Service-by-Service Functional Breakdown

| Service | Reused Base V1 Component | Minimum Required for Phase 2A/2B | Deferred Scope (Post-Phase 2) |
|---|---|---|---|
| **S1 Research Knowledge** | `schemas/evidence.py`<br>`schemas/decision.py`<br>`evidence/registry.py` | - Store Evidence Records for BindCraft (*Nature* 2025, DOI: `10.1038/s41586-025-09429-6`).<br>- Store Decision Record on BindCraft vs BindCraft2. | Automated PubMed API ingestion, vector embeddings for literature retrieval. |
| **S2 Target & Data** | `schemas/target.py`<br>`schemas/common.py`<br>`storage/database.py` | - Validate target structure file existence (`target.structure_file`).<br>- Export sanitized target PDB and format chains/hotspots into CLI arguments. | Automated cryptic pocket detection, target surface hydrophobicity mapping. |
| **S3 Generation** | `generators/base.py`<br>`schemas/candidate.py`<br>`core/pipeline.py` | - Implement `BindCraftGenerator` adhering strictly to `BaseGenerator`.<br>- Subprocess/Container execution boundary.<br>- Create candidates with initial status `CandidateStatus.GENERATED`. | Multi-modal diffusion (RFdiffusion integration), nanobody/VHH generation pipelines. |
| **S4 Prediction & Evaluation** | `predictors/base.py`<br>`validation/base.py`<br>`configs/base.yaml` | - Extract native BindCraft AF2 and PyRosetta metrics into `candidate.metrics`.<br>- Enforce scientific independence: internal score is NOT final validation; leave independent predictor slot open. | Full molecular dynamics (GROMACS/OpenMM 100ns relaxation), deep mutational scanning (DMS) modeling. |
| **S5 Diversity & Portfolio** | `schemas/candidate.py`<br>`diversity/clusters.py`<br>`schemas/common.py` | - Candidate metadata tagging (`generator_family: "bindcraft"`).<br>- Automated sequence-hash deduplication (`CandidateStatus.DUPLICATE`). | MMseqs2 sequence clustering (30/50/80% identity cutoffs), Foldseek structural clustering. |
| **S6 Experiment & Benchmark** | `schemas/experiment.py`<br>`core/pipeline.py`<br>`core/lifecycle.py` | - Subprocess timeout monitoring (SIGTERM/SIGKILL).<br>- Error taxonomy capture (`ErrorRecord`).<br>- Idempotent run resume without duplicate candidate generation. | Hyperparameter Bayesian optimization, cross-target automated benchmark harness. |
| **S7 Evidence & Provenance** | `provenance/tracker.py`<br>`storage/artifacts.py`<br>`storage/database.py` | - Populate `ProvenanceRecord` with container image digest, checkpoint hashes, seed, and config hash.<br>- Store FASTA, converted CIF, and execution logs in `candidates/{target_id}/{candidate_id}/`. | Cryptographic ledger / tamper-proof submission attestation generation. |

---

## 3. Detailed Adapter Specification: `BindCraftGenerator`

### 3.1 Class Architecture & Contract Adherence
Location: `src/protein_design/generators/bindcraft.py` (To be implemented in Phase 2B).

```python
class BindCraftGenerator(BaseGenerator):
    # Adapter for running BindCraft automated de novo binder design.
    # Adheres strictly to the frozen BaseGenerator contract:
    # generate(target: Target, config: dict[str, Any], num_candidates: int, seed: int) -> list[Candidate]
    pass
```

- **`name` Property:** `"bindcraft"`
- **`version` Property:** `"0.1.0-draft"` (Adapter version)
- **`design_type`:** `DesignType.MINIBINDER`
- **Upstream Code Reference:** `https://github.com/martinpacesa/BindCraft` at locked commit `06e12a443a5796a798935c13b246a4825946fa7c`.
- **Model Checkpoint Digests:**
  - AlphaFold2 Weights: `params_model_1.npz` through `params_model_5.npz` (~5.3 GB total).
  - ProteinMPNN Weights: `proteinmpnn_v_48_002.pt` (~50 MB).

### 3.2 Target Data Conversion & Exact JSON Settings Mapping
The adapter receives a `Target` schema instance and Base V1 execution parameters:
1. **Structure Validation:** Checks `target.structure_file`. If absent or non-existent on disk, raises `GeneratorConfigError("BindCraft requires an existing 3D structure file (.pdb or .cif)")`.
2. **Chain Isolation:** If `target.chains` are specified, ensures only target chains are preserved in the sanitized input PDB file passed to the container.
3. **Hotspot Formatting:** Converts `target.hotspots` (`list[HotspotInfo]`) into comma-separated string format (`"A120,A124"`).
4. **Exact Three-Tier Mapping Architecture:**
   Base Target field -> internal adapter field -> BindCraft settings JSON key:

| Base Target / Config Field | Internal Adapter Field | Upstream BindCraft Settings JSON Key | Type & Example | Description |
|---|---|---|---|---|
| `target.structure_file` | `target_pdb_path` | `starting_pdb` | String (`"/workspace/target.pdb"`) | Path to sanitized target structure (**NOT `"pdb"`**) |
| `target.chains` | `chains_str` | `chains` | String (`"A"` or `"A,B"`) | Comma-separated target chains (**NOT `"target_chains"`**) |
| `target.hotspots` | `hotspots_str` | `target_hotspot_residues` | String (`"A120,A124"`) or `null` | Residue numbers with chain prefix to guide interface loss |
| `config.generation.params.binder_lengths` | `lengths_list` | `lengths` | List of ints (`[50, 75]`) | Min/max bounds or discrete lengths for hallucinated binder |
| `num_candidates` (from `generate()`) | `num_final_designs` | `number_of_final_designs` | Integer (`10`) | Target quota of accepted designs passing all filters |
| `target.target_id` (sanitized) | `binder_name` | `binder_name` | String (`"PDL1_binder"`) | Prefix for design filenames and directory tagging |
| `output_dir` (run directory) | `design_path` | `design_path` | String (`"/workspace/output"`) | Directory where BindCraft saves trajectories and accepted designs |

*Prohibition Rule:* Upstream BindCraft at pinned commit `06e12a443a5796a798935c13b246a4825946fa7c` (verified via `settings_target/PDL1.json`) does NOT recognize keys `"pdb"` or `"target_chains"`. Using these invalid keys causes upstream silent failure or KeyError. All adapter serializers and test fixtures must strictly adhere to the exact upstream keys above.

### 3.3 Configuration Normalization & Command Generation
Configuration parameters are loaded from YAML under `generation.params`:

```yaml
generation:
  generator: bindcraft
  num_candidates: 10
  random_seed: 42
  params:
    runtime_mode: docker                               # Options: mock, docker
    container_image: "UNVERIFIED/TBD"                  # Upstream image unverified; requires local Dockerfile build or verified image digest
    binder_lengths: [50, 75]                           # Min/max binder length in amino acids
    design_rounds: 3                                   # ProteinMPNN sequence design rounds
    timeout_seconds: 7200                              # PROPOSED BUDGET (uncalibrated heuristic)
```

The adapter maps these parameters into a target settings JSON file (`/workspace/target_settings.json`):
```json
{
  "design_path": "/workspace/output",
  "binder_name": "target_binder",
  "starting_pdb": "/workspace/target.pdb",
  "chains": "A",
  "target_hotspot_residues": "A120,A124",
  "lengths": [50, 75],
  "number_of_final_designs": 10
}
```
And executes the verified upstream `bindcraft.py` CLI interface:
```bash
docker run --rm --gpus all \
  -v {host_workspace}:/workspace \
  -w /workspace \
  <UNVERIFIED_OR_LOCAL_IMAGE> \
  python -u /bindcraft/bindcraft.py \
  --settings /workspace/target_settings.json \
  --filters /workspace/filters.json \
  --advanced /workspace/advanced.json
```
*Verification Rule: Upstream argparse contains NO `--pdb`, `--target_chains`, `--hotspot`, `--lengths`, `--number_of_designs`, or `--seed` CLI arguments. All parameters are serialized inside JSON.*

### 3.4 Runtime Boundaries & Isolation Patterns

1. **`MockRunner`:** Injects pre-generated synthetic PDB and metric CSV files from `tests/fixtures/bindcraft_output/`. Enables instant unit testing, schema verification, and CI pipeline runs on CPU (latency: NOT MEASURED on host platform) without GPU hardware.
2. **`DockerRunner`:** Executes local container via `subprocess.Popen`. Captures stdout/stderr in real-time, monitors exit codes, isolates external dependencies, and manages timeouts.
3. **`CloudApiRunner`:** **DEFERRED (Post-Phase 2)**. Remote cluster dispatch is excluded from Phase 2B scope.

### 3.5 Output Parsing & Candidate Population
Upon process completion, the parser inspects the output directory (`design_path`):
1. **Candidate Sequence & Identification (Canonical Source-of-Truth):**
   - Upstream does **NOT** produce an `Accepted/final_designs.fasta` file.
   - The canonical source of truth for designed sequences is the **`Sequence`** column in `final_design_stats.csv` (cross-verified with coordinate residue sequences in `Accepted/*.pdb` or `Accepted/Ranked/*.pdb`).
   - Note: `mpnn_sequence` is strictly an internal Python loop variable name (`mpnn_sequence['seq']` in `bindcraft.py`), NOT a native CSV column header.
   - For each extracted sequence, calculates `sequence_hash = sha256(sequence)`.
   - Generates a deterministic candidate ID (`cand_XXXXXX`).
   - Generates downstream FASTA file (`candidates/{target_id}/{candidate_id}/sequence.fasta`) as an **optional convenience artifact**.
2. **Structure Artifact Conversion (PDB to mmCIF):**
   - BindCraft produces native `.pdb` files in `output/Accepted/` and `output/Accepted/Ranked/`.
   - **Mandatory Conversion:** The parser performs structural translation using an established library (Gemmi or BioPython PDBx/mmCIF):
     * Converts native binder PDB -> `candidates/{target_id}/{candidate_id}/binder.cif`.
     * Converts native complex PDB -> `candidates/{target_id}/{candidate_id}/complex.cif`.
     * **Prohibition:** Simply renaming `.pdb` to `.cif` without structural format conversion is strictly forbidden.
3. **Exact Metric Extraction Dictionary:**
   - Parses `output/final_design_stats.csv` generated by `generate_dataframe_labels()` in `functions/generic_utils.py:16–38`.
   - Maps exact upstream native column names to internal fields, explicitly separating raw values from transformed scales:
     * `candidate.metrics["raw_af2_plddt"] = float(row["Average_pLDDT"])` (raw ColabDesign scale: **0.0–1.0 float**, rounded to 2 decimals, threshold `0.80`)
     * `candidate.metrics["af2_plddt"] = float(row["Average_pLDDT"]) * 100.0` (explicit internal transformed presentation scale: 0.0–100.0)
     * `candidate.metrics["af2_ptm"] = float(row["Average_pTM"])` (scale 0.0–1.0)
     * `candidate.metrics["af2_iptm"] = float(row["Average_i_pTM"])` (scale 0.0–1.0, threshold `0.80`; used for `Accepted/Ranked/` sorting)
     * `candidate.metrics["af2_pae"] = float(row["Average_pAE"])` (raw ColabDesign scale: **0.0–1.0 normalized error**, divided by 31.0, threshold `0.35`, **NOT Ångströms**)
     * `candidate.metrics["af2_interface_pae"] = float(row["Average_i_pAE"])` (raw ColabDesign scale: **0.0–1.0 normalized error**, divided by 31.0, threshold `0.35`, **NOT Ångströms**)
     * `candidate.metrics["af2_interface_plddt"] = float(row["Average_i_pLDDT"])` (scale 0.0–1.0 float)
     * `candidate.metrics["af2_ss_plddt"] = float(row["Average_ss_pLDDT"])` (scale 0.0–1.0 float)
     * `candidate.metrics["unrelaxed_clashes"] = int(float(row["Average_Unrelaxed_Clashes"]))` (integer count)
     * `candidate.metrics["relaxed_clashes"] = int(float(row["Average_Relaxed_Clashes"]))` (integer count)
     * `candidate.metrics["binder_energy_score"] = float(row["Average_Binder_Energy_Score"])` (REU)
     * `candidate.metrics["surface_hydrophobicity"] = float(row["Average_Surface_Hydrophobicity"])` (fraction 0.0–1.0)
     * `candidate.metrics["pyrosetta_interface_sc"] = float(row["Average_ShapeComplementarity"])` (scale 0.0–1.0, Lawrence & Colman $S_c$)
     * `candidate.metrics["pyrosetta_interface_packstat"] = float(row["Average_PackStat"])` (scale 0.0–1.0)
     * `candidate.metrics["pyrosetta_interface_dg"] = float(row["Average_dG"])` (scale: **REU - Rosetta Energy Units, empirical statistical potential, NEVER kcal/mol, NEVER renamed to ddG**)
     * `candidate.metrics["pyrosetta_interface_dsasa"] = float(row["Average_dSASA"])` (scale: **$\text{Å}^2$ - square Ångströms**)
     * `candidate.metrics["pyrosetta_dg_dsasa"] = float(row["Average_dG/dSASA"])` (scale: $\text{REU}/\text{Å}^2$)
     * `candidate.metrics["interface_sasa_pct"] = float(row["Average_Interface_SASA_%"])` (scale 0.0–100.0%)
     * `candidate.metrics["hotspot_rmsd"] = float(row["Average_Hotspot_RMSD"])` (scale: Å)
     * `candidate.metrics["target_rmsd"] = float(row["Average_Target_RMSD"])` (scale: Å)
     * `candidate.metrics["binder_rmsd"] = float(row["Average_Binder_RMSD"])` (scale: Å)
     * Individual model metrics `{1..5}_<label>` stored in `candidate.metadata["model_metrics"][model_num][label]`.
4. **Lifecycle Initial State:**
   - Initializes candidate in `CandidateStatus.GENERATED` with reason `"bindcraft_generation_completed"`.
   - **Lifecycle Guard:** The adapter does NOT promote candidates to `VALID`.

### 3.6 Rejected Data Inventory & Trajectory Accounting
Upstream BindCraft produces comprehensive negative design artifacts across execution:
1. **Aggregate Rejection Counters (`failure_csv.csv` & stdout):** Records cumulative failure tallies per filter threshold (`Trajectory`, `Length`, `pLDDT`, `Contact_Loss`, `Clash`, `Rosetta_dG`, etc.). Ingested into `ExperimentRun.output_summary["rejection_counts"]`.
2. **Trajectory-Level Metadata (`trajectory_stats.csv`):** Captures complete optimization trajectory statistics across all attempted hallucination rounds.
3. **Candidate-Level Rejected Artifacts (`Rejected/*.pdb` & `mpnn_design_stats.csv`):** Candidate PDB files of ProteinMPNN redesigns failing downstream filters are preserved directly in `output/Rejected/` via upstream `shutil.copy(best_model_pdb, design_paths["Rejected"])` (`bindcraft.py:427`). Metrics for all redesigns are recorded in `mpnn_design_stats.csv`. These candidate-level artifacts provide authentic negative samples for ML failure-mode analysis.
4. **Trajectory Rejection PDBs (`Trajectory/LowConfidence/` & `Trajectory/Clashing/`):** Intermediate backbone models discarded during hallucination.
5. **Accepted Candidate Artifacts (`Accepted/*.pdb`, `Accepted/Ranked/*.pdb`, `final_design_stats.csv`):** Complexes passing all filters, ingested into `Candidate` records.
6. **Unavailable / Unobservable Failures:** Early divergence before coordinates are written to disk.

**Strict Rejection Accounting Policy:** The adapter **MUST NOT** manufacture phantom candidate records (`cand_000001`...) in the `Candidate` database for unaccepted trajectories, nor invent a non-existent `rejected_designs.csv` file. Discarded design metrics are stored under `ExperimentRun` metadata, and candidate-level rejected PDBs are indexed within research negative dataset partitions.

### 3.7 Timeout, Cancellation & Partial Results Handling
- Subprocess execution is managed with `subprocess.Popen` wrapped in an execution supervisor.
- If `timeout_seconds` is exceeded or cancellation is requested:
  1. Issues `SIGTERM` to the container process.
  2. If process remains responsive after a 10-second grace period, escalates to `SIGKILL` to prevent orphan/zombie containers.
  3. Scans `output/Accepted/` for any candidates that fully completed prior to termination.
  4. Ingests and registers valid completed candidates in SQLite DB.
  5. Marks `ExperimentRun` status as `PARTIAL` (if some candidates completed) or `FAILED`, attaching an `ErrorRecord`.

### 3.8 Identity Separation, Seed Limits & Idempotency
- **Request ID (`request_id`):** Identifies the design request. Cannot be derived from ungenerated sequences.
- **Run ID (`run_id`):** Identifies the execution run attempt (`ExperimentRun.run_id`).
- **Candidate ID (`candidate_id`):** Immutable ID for an ingested candidate (`cand_...`).
- **Sequence Hash (`sequence_hash`):** SHA-256 hash of the sequence.
- **Deduplication:** Before inserting, checks `MetadataStore.candidate_exists_by_hash(sequence_hash)`. If a candidate with identical sequence hash already exists, marks new candidate `CandidateStatus.DUPLICATE`.
- **Seed Control Reality & Five-Concept Disentanglement:**
  1. *Base API Seed:* The `seed` parameter passed into `BaseGenerator.generate(..., seed)`. Because upstream `bindcraft.py` exposes NO `--seed` flag, it does NOT control upstream pipeline trajectories end-to-end without wrapper intervention.
  2. *Upstream Trajectory Seed:* The dynamic integer sampled by `bindcraft.py:91` (`seed = int(np.random.randint(0, high=999999, size=1, dtype=int)[0])`) recorded in `final_design_stats.csv` under `Seed`.
  3. *Wrapper-Controlled Seed:* Interventions by the adapter (e.g. pre-seeding PRNG before script launch) to enforce reproducible runs.
  4. *Algorithmic Reproducibility vs Bitwise Determinism:* Re-runs with identical seed test algorithmic reproducibility within floating-point tolerance; cuDNN/JAX GPU atomic non-determinism prevents guarantees of bit-for-bit identical coordinates.
  5. *Cache Hit:* Re-reading an existing candidate from SQLite based on matching target and config hash is an **idempotent cache hit**, NOT an algorithmic reproduction test.

---

## 4. Scientific Warning & Phase 2B Fail-Closed Guard

### 4.1 System-Level Validation Warning
```text
[Real BindCraft Generator] --> Produces Real Candidate
                                        │
                                        ▼
                           [DummyPredictor (Base V1)] --> Returns Dummy Metrics
                                        │
                                        ▼
                           [DummyValidator (Base V1)] --> Always returns VALID
                                        │
                                        ▼
                     [Candidate Marked Status: VALID]
```

- **Architectural Reality:** In Phase 2B, when `BindCraftGenerator` is plugged into the Base V1 pipeline, generated candidates will pass through `DummyValidator` and be marked `VALID`.
- **Scientific Policy:** A candidate marked `VALID` by `DummyValidator` **DOES NOT CONSTITUTE A SCIENTIFICALLY VALIDATED BINDER**. Under `docs/scientific_principles.md`, its scientific status is strictly `COMPUTATIONALLY_GENERATED`. It must NEVER be reported as an experimentally or independently validated binder.

### 4.2 Phase 2B Blocking Requirement: Fail-Closed Export Guard with Purpose Separation
To prevent unvalidated or dummy-validated candidates from ever contaminating competition submissions or publication manuscripts, a mandatory fail-closed export guard is specified with strict objective separation:
```python
def verify_export_safety(candidate: Candidate, purpose: str = "competition") -> bool:
    """Fail-closed export gate separating competition delivery from publication.
    
    Args:
        candidate: Candidate record to verify.
        purpose: Export target objective ('competition' or 'publication').
        
    Raises:
        SecurityIntegrityError: If candidate fails validation checks or lacks required provenance.
    """
    validation_history = candidate.metadata.get("validation_history", [])
    
    # COMMON BLOCK 1: Dummy-only validation is unconditionally blocked for all exports
    if any("dummy" in v.lower() for v in validation_history):
        raise SecurityIntegrityError("Export blocked: Candidate passed only dummy validation.")
        
    # COMMON BLOCK 2: Missing or corrupted structure artifacts are unconditionally blocked
    if not candidate.structure_file:
        raise SecurityIntegrityError("Export blocked: Candidate structure coordinate file is missing.")
        
    # PURPOSE-SPECIFIC GATING
    if purpose == "publication":
        # Publication gate strictly mandates 9-link provenance and publication_ready = True
        if not candidate.provenance or not candidate.provenance.metadata.get("publication_ready", False):
            raise SecurityIntegrityError(
                "Export blocked for publication: Candidate not marked publication_ready with verified 9-link provenance."
            )
    elif purpose == "competition":
        # Competition gate validates competition submission eligibility and sequence length constraints
        # It does NOT mandate publication_ready = True, preserving operational flexibility for candidate library delivery
        if not candidate.sequence or len(candidate.sequence) == 0:
            raise SecurityIntegrityError(
                "Export blocked for competition: Candidate sequence is empty or invalid for submission."
            )
    else:
        raise ValueError(f"Unknown export purpose: {purpose}. Supported: 'competition', 'publication'.")
        
    return True
```
- **Phase 2B Test Gate:** Phase 2B must implement and verify `test_export_guard_blocks_dummy_validated_candidates` testing both `purpose="competition"` and `purpose="publication"`.
- **Base V1 Lifecycle Invariant:** This guard operates at the export/dispatch boundary and does **NOT** modify the frozen `CandidateStatus` enum.

---

## 5. Section D: Data & Evidence Requirements for Research Data Assets

To ensure that every candidate generated for the Changjiang Cup 2026 can simultaneously serve as validated empirical data for peer-reviewed publication, the adapter and storage pipeline enforce strict data capture, provenance tracking, and status taxonomy:

### 5.1 Observable Results & Raw Artifact Logging
Every generation trajectory must persist complete, unpruned primary outputs:
- **Primary Sequences:** Extracted from canonical source-of-truth (**`Sequence`** column in `final_design_stats.csv` or PDB coordinates); downstream FASTA format (`sequence.fasta`) generated as an optional artifact.
- **Structural Coordinates:** Converted mmCIF files for isolated binder (`binder.cif`) and complex (`complex.cif`) with atomic coordinates and B-factor pLDDT mappings.
- **Raw Metric Vectors:** Native score table (`final_design_stats.csv`) preserved without truncation, capturing all calculated metrics (`Average_pLDDT`, `Average_pTM`, `Average_i_pTM`, `Average_pAE`, `Average_i_pAE`, `Average_i_pLDDT`, `Average_ss_pLDDT`, `Average_Unrelaxed_Clashes`, `Average_Relaxed_Clashes`, `Average_Binder_Energy_Score`, `Average_Surface_Hydrophobicity`, `Average_ShapeComplementarity`, `Average_PackStat`, `Average_dG`, `Average_dSASA`, `Average_dG/dSASA`, `Average_Interface_SASA_%`, `Average_Hotspot_RMSD`, `Average_Target_RMSD`, `Average_Binder_RMSD`, plus `{1..5}_<label>`).
- **Execution Transcripts:** Complete stdout and stderr streams recorded in `candidates/{target_id}/runs/{run_id}/bindcraft_exec.log`.

### 5.2 Candidate Lineage & Nine-Link Provenance Graph
Every design is linked to an immutable, cryptographically verifiable `ProvenanceRecord` adhering to the complete Nine-Link Provenance Chain:
- **Lineage Tracking:** Derivative sequence redesigns track their parent backbone via `Candidate.parent_candidate`.
- **Reproducibility Metadata Fields:**
  1. `target_revision`: Target sequence, crystal structure PDB ID/chain, or epitope definition SHA-256 hash.
  2. `source`: Input origin, structural cleaning steps, and preprocessing log references.
  3. `experiment_run_id`: UUID linking to `ExperimentRun` in SQLite metadata store.
  4. `config_hash`: SHA-256 hash of complete JSON runtime configuration.
  5. `code_commit`: Git commit SHA of executing code.
  6. `model_weights_identity`: Checksum and identifier of AF2 and ProteinMPNN weights.
  7. `seed`: Random seed for algorithmic reproducibility tracking.
  8. `raw_artifact_hash`: SHA-256 checksum of raw output directory / files.
  9. `analysis_script`: Path and commit SHA of script generating reported statistics.
- **Scientific Integrity Gate (`publication_ready`):**
  - Stored in `ProvenanceRecord.metadata["publication_ready"]` (boolean).
  - Defaults to `False`. Evaluates to `True` only when all 9 provenance links, license verification, claim type, and evidence levels are verified. Missing any required element mandates `publication_ready = False`.

### 5.3 Six-Category Failure Retention & Trajectory Accounting
Negative outcomes and failed designs are preserved as valuable scientific assets:
- **Six-Category Taxonomy:**
  1. `computational_rejection`: Trajectories discarded during in silico generation by internal filters (AF2 pLDDT, contact distance, PyRosetta $\Delta G$).
  2. `execution_failure`: Unhandled runtime exceptions, CUDA OOM (exit code 137), timeouts, container launch errors.
  3. `untested`: Computationally generated candidates awaiting physical synthesis or assay.
  4. `assay_negative`: Synthesized candidates tested in wet-lab with no detectable binding.
  5. `assay_inconclusive`: Assays yielding ambiguous signals, high background noise, or aggregation.
  6. `expression_qc_failure`: Wet-lab protein synthesis failure or QC purity check failure.
- **Rejection Accounting:** BindCraft internal trajectory rejection counts are ingested into `ExperimentRun.output_summary["rejection_counts"]`.
- **In Silico Boundary Rule:** Trajectories labeled `computational_rejection` **MUST NOT** be reported as biological negative data without experimental assay verification.

### 5.4 Resource, Computational Cost & Error Tracking
- **Compute Accounting:** Execution duration (wall time in seconds), GPU model, and candidate generation throughput are recorded on `ExperimentRun`.
- **Structured Error Taxonomy:** Any non-zero exit codes (e.g. exit 137 OOM), timeout terminations, or syntax failures are logged via `ErrorRecord` with full stack traces, marking runs as `PARTIAL` or `FAILED` without data corruption.

### 5.5 Scientific Status Hierarchy & State Separation
In strict compliance with `docs/scientific_principles.md`:
1. `UNTESTED` / `GENERATED`: Model produced the sequence/backbone. Zero validation performed.
2. `IN_SILICO_FILTERED` / `REJECTED`: Discarded by computational QC with exact stage and threshold recorded.
3. `COMPUTATIONALLY_VALIDATED`: Passed orthogonal independent structural predictor and physics checks.
4. `EXPERIMENTALLY_TESTED`: Synthesized and tested in wet-lab biophysical assay (competition screening).
5. `EXPERIMENTALLY_VALIDATED`: Confirmed by quantitative binding curves (SPR, BLI, ITC, ELISA).

### 5.6 Experimental Attribution & External Baselines
- **Attribution Policy:** When wet-lab assays are performed by competition organizers or external partners, the executing entity must be explicitly named. The team must never claim in-house wet-lab execution if not performed.
- **No Inferred Affinity:** In vitro $K_d$ or binding affinity constants cannot be inferred from leaderboard ranking or binary competition outcomes.
- **External Baselines:** Strictly segregated into `LITERATURE_REPORTED`, `SOURCE_VERIFIED`, `LOCALLY_REPRODUCED`, and `PROJECT_BENCHMARKED`. Only `PROJECT_BENCHMARKED` represents project-executed baseline performance.

### 5.7 Explicit Upstream Data Limitations
The adapter documentation explicitly identifies data that upstream BindCraft **CANNOT** provide:
- **No Molecular Dynamics Trajectories:** BindCraft performs static AF2 backpropagation and PyRosetta FastRelax; it does not perform explicit solvent MD relaxation (e.g. 100ns GROMACS/OpenMM).
- **No Physical Thermodynamic Entropy:** Rosetta $\Delta G$ (REU) is an empirical statistical potential, not a rigorous free energy perturbation (FEP) calculation.
- **No Off-Target Cross-Reactivity Profiling:** BindCraft models the isolated target-binder complex only; it provides zero predictions regarding off-target binding across the human or host proteome.

---

## 6. Section D: Correction Log & Source Evidence Matrix

| Finding ID | Previous Erroneous Claim / Draft Text | Corrected Evidence-Grounded Text | File & Section | Primary Evidence Source | Status | Rationale for Open Status |
|---|---|---|---|---|---|---|
| **FINDING-C1-01** | Cited BindCraft as *Nature Biotechnology* (2024) | Corrected to *Nature* 646, 483–492 (2025). DOI: `10.1038/s41586-025-09429-6`. Title: *One-shot design of functional protein binders with BindCraft*. | `RESEARCH.md` §2, `READINESS.md` §2.1 | Pacesa et al., *Nature* 646 (2025) | **RESOLVED** | N/A |
| **FINDING-C2-01** | Upstream repository unpinned | Pinned full commit SHA `06e12a443a5796a798935c13b246a4825946fa7c` | `RESEARCH.md` §2, `SPECIFICATION.md` §3.1 | `martinpacesa/BindCraft` git log | **RESOLVED** | N/A |
| **FINDING-C3-01** | Assumed PDB files could be stored as CIF by changing file extension | Mandated structural conversion via Gemmi/BioPython parser | `SPECIFICATION.md` §3.5 | Base V1 storage contract | **RESOLVED** | N/A |
| **FINDING-C4-01** | Predicted computational metrics conflated with binding affinity | Explicitly classified pLDDT, i_pTM, dG as computational predictions, not wet-lab Kd | `RESEARCH.md` §3.3, `SPECIFICATION.md` §3.5 | `docs/scientific_principles.md` | **RESOLVED** | N/A |
| **FINDING-C5-02** | Claimed `--no-pyrosetta` OpenMM fallback mode was ready | Marked `--no-pyrosetta` as **DEFERRED / UNVERIFIED IN UPSTREAM** | `RESEARCH.md` §4.2, `SPECIFICATION.md` §3.3 | BindCraft upstream source code | **RESOLVED** | N/A |
| **FINDING-C7-01** | Equated database cache hit with seed-based algorithmic reproducibility | Decoupled cache hit from seed reproducibility on GPU hardware | `SPECIFICATION.md` §3.8 | Determinism principles | **RESOLVED** | N/A |
| **FINDING-C9-01** | Absence of formal scientific integrity and data ownership governance | Established Principles A through J, 9-link provenance chain, and `PUBLICATION_READY` gate | `RESEARCH.md` §7, `SPECIFICATION.md` §5 | Scientific integrity rules | **RESOLVED** | N/A |
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




