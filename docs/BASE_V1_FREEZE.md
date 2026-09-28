# Base V1 Specification & Freeze Document

**System:** AI Protein Design System — Changjiang Cup 2026  
**Freeze Date:** 2026-09-28  
**Branch:** `audit/base-v1`  
**Status:** **FROZEN**  

---

## 1. Core Versions

- **Architecture Version:** `1.0.0`
- **Schema Version:** `1.0.0`
- **Storage Version:** `1.0.0`
- **Pipeline Version:** `0.1.0`

---

## 2. Frozen Contracts & Interfaces

### 2.1 Core Orchestration Contract
Core execution logic in `src/protein_design/core/pipeline.py` is **FROZEN**.
Model integrations (generators, predictors, validators) MUST adapt to core interfaces rather than modifying core pipeline logic.

- **Generator Interface (`BaseGenerator`)**:
  ```python
  def generate(self, target: Target, config: dict[str, Any], num_candidates: int, seed: int) -> list[Candidate]
  ```
- **Predictor Interface (`BasePredictor`)**:
  ```python
  def predict(self, candidate: Candidate, target: Target, config: dict[str, Any]) -> PredictionResult
  ```
- **Validator Interface (`BaseValidator`)**:
  ```python
  def validate(self, candidate: Candidate, config: dict[str, Any]) -> ValidationResult
  ```

### 2.2 Lifecycle State Machine
Supported Candidate Statuses:
`CREATED` → `GENERATED` → `SEQUENCE_VALIDATED` → `STRUCTURE_PREDICTED` → `STRUCTURE_CHECKED` → `INTERFACE_CHECKED` → `DEVELOPABILITY_CHECKED` → `NOVELTY_CHECKED` → `VALID`

Terminal states: `VALID`, `REJECTED`, `FAILED`, `INVALID`, `DUPLICATE`.
Failed or rejected candidates are NEVER deleted from the metadata store.

### 2.3 Storage Layout
- **Metadata DB:** SQLite (`protein_design.db`) with WAL mode.
- **Artifact Store:** `candidates/{target_id}/{candidate_id}/` (containing `sequence.fasta`, `binder.cif`, `complex.cif`, `provenance.json`, and sub-artifacts).

---

## 3. Known Base V1 Limitations

1. **In-Memory Candidate Lists:** Batches process as python lists. For ultra-large runs (>50k candidates), stream/chunking will be added in Phase 2.
2. **Biological Clustering Placeholder:** `DiversityInfo` schema is populated with `generator_family`. Full alignment-based clustering (MMseqs2, Foldseek) is deferred to model integration phases.
3. **Scientific Threshold Calibration:** Scientific thresholds default to `null` ("compute but do not filter"). Calibration occurs per target family during real model integration.

---

## 4. Future Model Adapter Requirements

All real protein design tools MUST implement plugin adapters inheriting from:
- `protein_design.generators.base.BaseGenerator`
- `protein_design.predictors.base.BasePredictor`
- `protein_design.validation.base.BaseValidator`

**First Target Model Integration Candidate:** BindCraft / RFdiffusion + ProteinMPNN + AlphaFold2 / Chai-1.
