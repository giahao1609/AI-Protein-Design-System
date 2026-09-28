# Architecture — AI Protein Design System

## Overview

This system follows a modular, pipeline-based architecture designed for mass generation of diverse protein binder candidates.

## Design Principles

1. **Generate many, not one** — The system is optimized for producing large libraries, not single best candidates.
2. **Diversity matters** — Redundant sequences are not a library. Diversity is tracked across sequence, structure, interface, binding mode, and generator.
3. **AI output is not truth** — All scientific claims follow: CLAIM → EVIDENCE → INDEPENDENT CHECK → BENCHMARK → DECISION.
4. **Independent validation** — The model that generates a candidate cannot be the sole evaluator.
5. **Reproducibility** — Every candidate is traceable to its exact origin (model, version, config, seed, commit).
6. **Config-first** — No scientific thresholds hardcoded in Python. All thresholds come from benchmarked, calibrated config files.

## Pipeline Architecture

```
Target
  ↓
Target Analysis
  ↓
Generator (abstract interface)
  ↓
Candidate Library (batch)
  ↓
Structure Predictor (abstract interface)
  ↓
Validator (abstract interface)
  ├── Sequence QC
  ├── Structure QC
  ├── Interface QC
  ├── Developability
  └── Novelty
  ↓
Storage (SQLite + Filesystem)
  ↓
Diversity Analysis
  ↓
Candidate Library
```

## Module Map

| Module | Responsibility |
|--------|---------------|
| `schemas/` | Pydantic data models (Target, Candidate, Run, Evidence, Decision) |
| `config/` | YAML config loading, merging, validation |
| `core/` | Pipeline orchestration, lifecycle state machine, exceptions |
| `generators/` | Abstract Generator interface + implementations |
| `predictors/` | Abstract Predictor interface + implementations |
| `validation/` | Abstract Validator interface + implementations |
| `diversity/` | Diversity clustering schemas and utilities |
| `provenance/` | Provenance tracking, hashing, hardware detection |
| `storage/` | SQLite metadata store + filesystem artifact store |
| `evidence/` | Evidence and decision record management |
| `logging/` | Structured logging configuration |
| `cli/` | Command-line interface |

## Storage Design

- **SQLite** for structured metadata (candidates, targets, runs, evidence, decisions)
- **Filesystem** for artifacts (FASTA, CIF, PDB, provenance JSON, logs)
- Layout: `candidates/{target_id}/{candidate_id}/`

## Error Isolation

One candidate failing does NOT crash the batch. The pipeline:
1. Catches exceptions per-candidate
2. Records the error with traceback
3. Marks the candidate as FAILED
4. Continues processing remaining candidates
5. Reports partial completion

## Checkpoint / Resume

- Pipeline checks existing candidate status before processing
- Terminal-status candidates are skipped on resume
- ExperimentRun tracks checkpoint state

## Adapter Pattern

All model integrations use abstract interfaces:
- `BaseGenerator` → DummyGenerator, BindCraftGenerator, RFdiffusionGenerator, ...
- `BasePredictor` → DummyPredictor, AlphaFold2Predictor, ChaiPredictor, ...
- `BaseValidator` → DummyValidator, StructureValidator, InterfaceValidator, ...
