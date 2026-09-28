# AI Protein Design System
## Changjiang Cup 2026 — Phase 0: BASE V1

A modular, scientifically auditable platform for de novo protein binder design.

**Goal**: Build a research foundation capable of generating, managing, validating, and improving a large, diverse library of protein binder candidates.

### Current Phase: BASE V1

BASE V1 establishes the software/research foundation:

- **Schemas** — Target, Candidate, ExperimentRun, EvidenceRecord, DecisionRecord
- **Config-first** — No scientific thresholds hardcoded in Python
- **Storage** — SQLite metadata + filesystem artifacts, scalable to 100k+ candidates
- **Provenance** — Every candidate traceable to model, version, seed, config, commit
- **Pipeline** — Modular stages with abstract Generator/Predictor/Validator interfaces
- **Dummy backends** — Full end-to-end testing without real protein models
- **Candidate lifecycle** — State machine with complete transition history
- **Error isolation** — One candidate failing does not crash the batch
- **Resume/checkpoint** — No full re-runs on partial failure
- **Structured logging** — JSON-formatted, contextual logging
- **Audit trail** — Versioned scientific decisions

### Quick Start

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Linux/Mac

# Install in development mode
pip install -e ".[dev]"

# Run dummy pipeline demo
protein-design run demo

# List candidates
protein-design candidate list

# Run tests
pytest
```

### Architecture

See [docs/architecture.md](docs/architecture.md) for full architecture documentation.

### Scientific Principles

See [docs/scientific_principles.md](docs/scientific_principles.md) for the scientific framework.

### Project Structure

```
src/protein_design/
├── core/           # Pipeline orchestration, lifecycle
├── schemas/        # Pydantic data models
├── config/         # Config loading & validation
├── generators/     # Generator adapter interface
├── predictors/     # Predictor adapter interface
├── validation/     # Validator adapter interface
├── diversity/      # Diversity analysis
├── provenance/     # Provenance tracking & hashing
├── storage/        # SQLite + filesystem storage
├── evidence/       # Evidence & decision records
├── logging/        # Structured logging
└── cli/            # CLI commands
```

### License

MIT
