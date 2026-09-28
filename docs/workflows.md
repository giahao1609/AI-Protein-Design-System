# Workflows — AI Protein Design System

## Demo Pipeline Workflow

```bash
protein-design run demo --num 10 --seed 42
```

This runs the full dummy pipeline:

```
1. Create demo target (hardcoded sequence)
2. DummyGenerator produces 10 random sequences
3. DummyPredictor generates fake pLDDT/pTM/ipTM scores
4. DummyValidator checks metrics against config thresholds
5. All candidates stored in SQLite + filesystem
6. Results displayed in terminal
```

## Adding a Target

```bash
protein-design target add target.yaml
```

Target YAML format:
```yaml
name: "My Target Protein"
source: "PDB:7XYZ"
sequence: "MKTVRQERLKSIVRILERSKEPV..."
source_references:
  - "PDB:7XYZ"
  - "doi:10.1234/example"
```

## Inspecting Candidates

```bash
# List all candidates
protein-design candidate list

# Filter by target
protein-design candidate list --target test_target_001

# Filter by status
protein-design candidate list --status VALID

# Inspect a specific candidate
protein-design candidate inspect cand_000001
```

## Future Workflows (Post-BASE)

```bash
# Run with real models
protein-design run --config configs/production.yaml --target targets/target_001.yaml

# Benchmark
protein-design benchmark run benchmark_001

# Audit report
protein-design audit report
```
