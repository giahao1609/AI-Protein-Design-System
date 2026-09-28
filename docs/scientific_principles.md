# Scientific Principles — AI Protein Design System

## Core Principle: AI Output Is Not Truth

Every scientific conclusion in this system must follow:

```
CLAIM → EVIDENCE → INDEPENDENT CHECK → BENCHMARK → DECISION
```

"AI said so" is never sufficient scientific evidence.

## Evidence Hierarchy

Sources are ranked by reliability (1 = most reliable):

| Level | Source Type | Example |
|-------|-----------|---------|
| 1 | Experimental wet-lab evidence | Binding assay results, SPR data |
| 2 | Experimental databases | PDB structures, curated datasets |
| 3 | Peer-reviewed papers | Published in Nature, Science, etc. |
| 4 | Independent computational evidence | Validated by separate method |
| 5 | Preprints | bioRxiv, arXiv |
| 6 | Model documentation / GitHub | Tool README, release notes |
| 7 | AI reasoning | LLM output, model predictions |

**AI reasoning is always the LEAST reliable source.**

## Scientific Status Labels

Labels have strict definitions:

| Label | Meaning |
|-------|---------|
| `GENERATED` | Model produced this candidate. No validation. |
| `COMPUTATIONALLY_VALIDATED` | Passed independent computational checks. |
| `EXPERIMENTALLY_TESTED` | Wet-lab experiment performed. |
| `EXPERIMENTALLY_VALIDATED` | Wet-lab result confirms binding claim. |

**Forbidden language without experimental evidence:**
- ~~"functional"~~
- ~~"successful"~~
- ~~"binds strongly"~~
- ~~"validated"~~ (without "computationally" qualifier)

## Independent Validation

The model that generates a candidate must NOT be the sole evaluator:

```
Generator A → Candidate → Predictor B + Predictor C + Physics analysis + Sequence checks + Novelty search
```

## Threshold Calibration

No scientific threshold is assumed. The workflow is:

```
1. Benchmark with known cases
2. Calibrate thresholds from benchmark data
3. Record thresholds in config (with evidence)
4. Apply thresholds in pipeline
```

Until benchmarked, all thresholds are `null` (compute but do not filter).

## Reproducibility Requirements

Every candidate must be traceable to:
- Target protein
- Generator model + version + checkpoint
- Git commit of the code
- Full configuration (hashed)
- Random seed
- Hardware environment
- Timestamp
- Parent candidate (if derivative)
