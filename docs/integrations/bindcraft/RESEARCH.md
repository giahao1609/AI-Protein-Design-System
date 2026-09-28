# BindCraft Model Integration Research Report

**Model Name:** BindCraft (Automated *De Novo* Protein Binder Design)  
**Developers:** Pacesa Lab (Martin Pacesa et al., EPFL)  
**Repositories:** 
- Original: `https://github.com/martinpacesa/BindCraft`
- Next-Gen: `https://github.com/PacesaLab/BindCraft2`  
**Research Date:** 2026-09-28  
**Integration Target Phase:** Phase 2 (Adapter implementation for Base V1)  

---

## 1. Overview & Scientific Principles

BindCraft is an open-source, end-to-end pipeline for *de novo* protein binder design. Unlike pure diffusion-based workflows (e.g., RFdiffusion alone), BindCraft uses **backpropagation through AlphaFold2** (AF2 hallucination/refinement) to directly optimize binder backbone structures and interface contacts against target surfaces.

### Workflow Stages:
1. **Target Specification & Hotspots:** User specifies target PDB, chain, and optional target hotspot residues.
2. **AF2 Backbone Hallucination & Refinement:** Backpropagation through AF2 loss functions optimizes seed sequences to bind target hotspots.
3. **Sequence Redesign with ProteinMPNN:** ProteinMPNN generates high-affinity sequence candidates for the hallucinated binder backbones.
4. **Physics-Based Filtering with PyRosetta:** PyRosetta calculates binding free energy ($\Delta G$), shape complementarity ($S_c$), interface packing, and clash metrics.
5. **ColabFold / AF2 Validation:** Independent structure prediction of designed sequences to confirm folded binder state and complex pLDDT / ipTM scores.

---

## 2. Technical Dependencies & Requirements

### 2.1 Software & Runtime Environment
- **Operating System:** Linux (Ubuntu 20.04/22.04 LTS). *Windows native unsupported.*
- **Python Version:** Python 3.10 / 3.11.
- **CUDA:** CUDA 11.8 or 12.4+.
- **Core Frameworks:** PyTorch, JAX / JAXLIB (with CUDA support), OpenMM.
- **Scientific Packages:** 
  - ColabFold / AlphaFold2 weights (~5.3 GB)
  - ProteinMPNN
  - PyRosetta 3 (C++ Python bindings)
  - Biopython, SciPy, NumPy, Pandas, PyYAML

### 2.2 Model Weights & Disk Footprint
- **AlphaFold2 Weights:** ~5.3 GB (Params: `params_model_1.npz` through `params_model_5.npz`, `params_model_1_ptm.npz`, etc.).
- **ProteinMPNN Weights:** ~50 MB (`proteinmpnn_v_48_002.pt`, etc.).
- **Conda Environment / Docker Image:** ~12–15 GB.
- **Total Storage Required:** ~20 GB.

### 2.3 Hardware & Memory Requirements
- **Recommended VRAM:** **16 GB to 24 GB+ VRAM** (NVIDIA RTX 3090 / RTX 4090 / A100 / L40S).
- **Minimum VRAM:** 8–12 GB VRAM for short minibinders (<60 AAs) with `--low-vram` options.
- **Local Machine Constraints (RTX 3050 4GB VRAM):** Local GPU has 4 GB VRAM. Direct execution of full AF2 backpropagation will result in CUDA Out-Of-Memory (OOM) errors unless restricted to tiny peptide fragments or offloaded to cloud GPUs.

---

## 3. Licensing & Compliance Matrix

| Component | License Type | Commercial Use | Operational Impact |
|---|---|---|---|
| **BindCraft Code** | MIT / Open-Source | Allowed | Free to use and integrate via adapter. |
| **AlphaFold2 Weights** | CC-BY 4.0 | Allowed | Models require attribution. Weights download script available. |
| **ProteinMPNN** | MIT | Allowed | Fully permissive open source. |
| **PyRosetta** | PyRosetta Academic / Non-Commercial License | **Restricted** (Requires license for commercial use) | Free for academic/research competitions. Alternative: FreeBindCraft mode (`--no-pyrosetta`) using open-source tools. |

---

## 4. Integration Architecture with Frozen Base V1

To strictly adhere to Base V1 freeze rules, BindCraft will be integrated via a custom `BaseGenerator` adapter class without modifying core code.

### 4.1 Adapter Interface (`BindCraftGenerator`)
Location: `src/protein_design/generators/bindcraft.py` (To be created in Phase 2B).

```text
Pipeline (Core V1 - Frozen)
   │
   ▼
BindCraftGenerator.generate(target, config, num_candidates, seed)
   │
   ├── 1. Export Target PDB & JSON configuration to candidate temp workspace
   ├── 2. Launch WSL2 / Docker Subprocess:
   │      docker run --gpus all -v /data:/data bindcraft:v1 \
   │        --target target.pdb --chains A --hotspots "A120,A124" ...
   ├── 3. Monitor execution & capture structured logs
   ├── 4. Read output FASTA, PDB/CIF complex structures, and PyRosetta metrics
   └── 5. Return list[Candidate] with status = CREATED / GENERATED and populated ProvenanceRecord
```

### 4.2 Candidate & Provenance Mapping
- `generator`: `"bindcraft"`
- `generator_version`: `"1.0.0"`
- `provenance.model_checkpoint`: `"alphafold2_ptm + proteinmpnn_v_48_002"`
- `provenance.config_hash`: SHA-256 hash of BindCraft pipeline config.
- `structure_path`: `candidates/{target_id}/{candidate_id}/binder.cif`
- `complex_structure_path`: `candidates/{target_id}/{candidate_id}/complex.cif`

---

## 5. Risk Assessment & Mitigation Strategies

1. **Risk:** CUDA Out-Of-Memory (OOM) on local 4GB RTX 3050 GPU.  
   **Mitigation:** Implement dual-runtime configuration in `BindCraftGenerator`:
   - `mode: "local_mock"` (For local unit testing without GPU crash)
   - `mode: "wsl2_docker"` (For small minibinders <50 AAs)
   - `mode: "cloud_api"` (For full production runs on 24GB VRAM cloud instances via Modal / RunPod API).

2. **Risk:** PyRosetta Licensing restrictions.  
   **Mitigation:** Support `--no-pyrosetta` flag in config to fallback to OpenMM / FoldX shape complementarity scoring when PyRosetta license is absent.

3. **Risk:** Long execution times blocking synchronous CLI.  
   **Mitigation:** Core pipeline already supports candidate status saving and checkpoint resume. Interrupted generation jobs resume cleanly.

---

## 6. Next Implementation Steps (Phase 2B)

1. Create Dockerfile / WSL2 environment recipe for BindCraft runtime (`docker/bindcraft.Dockerfile`).
2. Implement `BindCraftGenerator` class adhering to `BaseGenerator` interface.
3. Write unit & integration tests (`tests/unit/test_bindcraft_adapter.py`) using mock outputs.
4. Benchmark single minibinder candidate generation on small demo target.
