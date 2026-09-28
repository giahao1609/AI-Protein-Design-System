# Base V1 System Audit Report

**System Name:** AI Protein Design System — Changjiang Cup 2026  
**Audit Date:** 2026-09-28  
**Audit Phase:** Phase 1 — Base V1 Audit, Hardening & Freeze  
**Branch:** `audit/base-v1`

---

## 1. Executive Summary

This audit evaluates the Base V1 architecture, schemas, candidate lifecycle, storage, failure handling, reproducibility, provenance, configuration, and test coverage before integrating real protein models (such as BindCraft, RFdiffusion, ProteinMPNN, AlphaFold, Chai, or Rosetta).

The initial Base V1 codebase provides a solid, modular foundation with clean abstractions separating core orchestration from generator, predictor, and validator backends. However, several critical architectural gaps, lifecycle bugs, and resume/scalability edge cases were identified during this audit.

---

## 2. Subsystem Audit Matrix

| Subsystem | Rating | Summary & Findings |
|---|---|---|
| **Architecture & Coupling** | **PASS** | Core orchestration (`Pipeline`) is completely decoupled from model-specific tools (no hard dependencies on RFdiffusion, AlphaFold, etc.). Plugin interfaces (`BaseGenerator`, `BasePredictor`, `BaseValidator`) are clean. |
| **Data Schemas** | **WARNING** | `Target`, `Candidate`, `ExperimentRun`, `EvidenceRecord`, `DecisionRecord` are comprehensive with Pydantic v2 validation. However, `CandidateStatus.INVALID` cannot be transitioned to due to a missing entry in `VALID_TRANSITIONS`. |
| **Candidate Lifecycle** | **WARNING** | `StatusTransition` tracking works well, but `VALID_TRANSITIONS` map omits `INVALID` as a valid destination for `CREATED`, `GENERATED`, `SEQUENCE_VALIDATED`, causing `CandidateLifecycleError` when invalid candidates are encountered. |
| **Storage & Scaling** | **PASS** | SQLite metadata store with WAL mode handles fast queries. Filesystem artifact layout `candidates/{target_id}/{candidate_id}/` cleanly separates structured data from heavy binary/text artifacts. Scalable to 10^4-10^5 metadata records. |
| **Provenance & Deduplication** | **WARNING** | `ProvenanceRecord` captures git commit, config hash, hardware, seed, and input hashes. However, `sequence_hash` deduplication is implemented in `MetadataStore` but not automatically invoked in `Pipeline` generation/validation stages. |
| **Checkpoint & Resume** | **FAIL** | Resuming an interrupted run skips candidate prediction if terminal, but `_stage_generate` re-generates new candidate IDs on resume instead of reusing existing candidates from the run record. |
| **Error Isolation & Stress** | **WARNING** | Individual candidate exceptions during prediction/validation are caught and logged without crashing the batch. However, generator exceptions crash the whole run, and failure injection modes (predictor crash, timeout, invalid artifact) are not built into dummy backends. |
| **Configuration & Thresholds** | **PASS** | No scientific thresholds are hardcoded in Python modules. All thresholds default to `null` in `configs/base.yaml` ("compute but do not filter until calibrated"). |
| **CLI & User Experience** | **WARNING** | `protein-design run demo`, `target list/add`, `candidate list/inspect`, and `audit report` commands exist. `run inspect <id>` is currently missing from the CLI. |
| **Test Coverage** | **WARNING** | 64 unit/integration tests pass. However, there are no tests for 1,000+ candidates mass creation, failure injection, interrupted run resume, or sequence deduplication. |
| **Scalability Assumptions** | **WARNING** | Database queries use pagination (`limit`/`offset`), but batch candidate generation and DB commits process in a single list in memory rather than streaming/chunking for large batches (e.g. 10,000 candidates). |

---

## 3. Detailed Findings & Required Hardening Actions

### 3.1 Lifecycle & Schema Deficiencies
- **Finding:** `CandidateStatus.INVALID` is declared in `CandidateStatus` enum and handled in terminal check, but `VALID_TRANSITIONS` in `src/protein_design/core/lifecycle.py` does not include `CandidateStatus.INVALID` in any state's transition set.
- **Action Needed:** Add `CandidateStatus.INVALID` to `VALID_TRANSITIONS` for `CREATED`, `GENERATED`, `SEQUENCE_VALIDATED`, `STRUCTURE_PREDICTED`, `STRUCTURE_CHECKED`, `INTERFACE_CHECKED`.

### 3.2 Checkpoint & Resume Logic
- **Finding:** When `pipeline.run(target, run)` is called with an existing `ExperimentRun`, `_stage_generate` runs `generator.generate(...)` again, generating new candidates with new IDs instead of reusing candidates already registered in `run.candidate_ids`.
- **Action Needed:** Update `_stage_generate` and `pipeline.run()` to load existing candidates from `db` when resuming a run, skipping re-generation if generation was already completed.

### 3.3 Deduplication Framework
- **Finding:** `MetadataStore.candidate_exists_by_hash(sequence_hash)` exists, but `Pipeline` does not check for duplicate candidate sequences during generation/validation.
- **Action Needed:** Integrate automatic sequence hash deduplication check in `Pipeline` validation stage to transition identical candidates to `CandidateStatus.DUPLICATE`.

### 3.4 Dummy Backend Failure Injection
- **Finding:** `DummyGenerator`, `DummyPredictor`, and `DummyValidator` produce deterministic mock data without support for simulating failures (e.g., corrupted CIF, predictor exception, invalid sequence, timeout).
- **Action Needed:** Add configurable failure injection parameters (e.g. `fail_candidate_ids`, `fail_rate`, `fail_stage`) to dummy backends to enable robust testing of pipeline error isolation.

### 3.5 CLI Commands
- **Finding:** `protein-design run inspect <run_id>` is missing from CLI commands in `src/protein_design/cli/main.py`.
- **Action Needed:** Add `run inspect <run_id>` command displaying run status, timing, hardware, config hash, error log summary, and produced candidates.

### 3.6 Mass Candidate & Stress Testing
- **Finding:** Unit and integration tests only test batches of up to 10 candidates.
- **Action Needed:** Create `tests/integration/test_mass_candidates.py` to test 1,000 candidates end-to-end, validating ID uniqueness, DB write throughput, query performance, and memory stability.

### 3.7 Failure Injection & Resume Testing
- **Finding:** No automated unit/integration tests verify pipeline recovery when individual candidates throw exceptions or when a run is interrupted midway.
- **Action Needed:** Create `tests/integration/test_failure_injection.py` and `tests/integration/test_resume.py`.

---

## 4. Technical Debt Inventory

1. **Memory Buffering in Pipeline:** Generator returns `list[Candidate]` all at once. For 10,000+ candidates, batch generator should yield/chunk candidates.
2. **Database Batch Inserts:** `save_candidate` commits per candidate. Bulk insert method `save_candidates_batch` will significantly speed up 1,000+ candidate writes.
3. **Diversity Clustering Interface:** `DiversityInfo` schema is populated only with `generator_family`; external cluster alignment tools (MMseqs2 / Foldseek) are placeholders until real model phase.
4. **Competition Rule Integration:** `competition/rule_registry.yaml` is maintained separately from core schemas, ensuring core code does not rely on unconfirmed competition rules.

---

## 5. Next Steps Plan

1. **Fix Candidate Lifecycle:** Update `VALID_TRANSITIONS` in `lifecycle.py` to allow `INVALID` status transitions.
2. **Harden Pipeline & Resume:** Update `Pipeline` to support resuming existing runs without duplicate generation, batch DB inserts, and sequence deduplication.
3. **Enhance Dummy Backends:** Add failure injection flags to `DummyGenerator`, `DummyPredictor`, and `DummyValidator`.
4. **Implement CLI `run inspect`:** Add `protein-design run inspect <id>` command.
5. **Add Comprehensive Tests:**
   - 1,000 candidate mass stress test (`test_mass_candidates.py`)
   - Failure-injection resilience test (`test_failure_injection.py`)
   - Run resume verification test (`test_resume.py`)
   - Reproducibility test (`test_reproducibility.py`)
6. **Verify End-to-End Demo & Benchmark:** Run 100+ candidate demo and 1,000 candidate stress test.
7. **Freeze Base V1:** Produce `docs/BASE_V1_FREEZE.md`.
