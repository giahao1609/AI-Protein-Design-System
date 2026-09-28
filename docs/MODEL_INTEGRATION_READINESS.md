# Model Integration Readiness Assessment

**System:** AI Protein Design System — Changjiang Cup 2026  
**Assessment Date:** 2026-09-28  
**Phase:** Phase 2A — BindCraft Model Integration Research & Readiness  
**Target Model:** BindCraft (Pacesa Lab)  

---

## 1. Local Hardware & System Inspection Summary

| Resource | Detected Specification | Minimum BindCraft Req. | Status / Risk Level |
|---|---|---|---|
| **OS** | Windows 11 Home (Build 26200) | Linux (Ubuntu 20.04+) | ⚠️ **Unsupported Native**: Linux runtime required via WSL2/Docker. |
| **CPU** | Intel Core i5-11400H @ 2.70GHz (6C/12T) | 8+ Cores recommended | 🟡 **Acceptable**: Moderate CPU power available for preprocessing. |
| **RAM** | 16.0 GB Total (~5.8 GB free) | 16–32 GB RAM | 🟡 **Tight**: Sufficient for small targets (<100 AAs); large targets may swap. |
| **Disk Space** | 295.6 GB Total, **40.4 GB Free** (C:\) | ~20 GB (weights + env) | 🟡 **Adequate**: 40.4 GB free is sufficient if weights & containers are pruned. |
| **GPU & VRAM** | **NVIDIA RTX 3050 Laptop GPU (4 GB VRAM)** | **16–24 GB VRAM** (recommended) | 🔴 **HIGH BOTTLENECK**: 4GB VRAM restricts local execution to very short minibinders or requires cloud offloading (RunPod/Modal). |
| **Container / Virtualization** | WSL2 (Ubuntu 2.0+), Docker Desktop 29.5 | Docker / Conda (Linux) | ✅ **READY**: Docker & WSL2 installed and operational. |

---

## 2. Environment Compatibility & Isolation Strategy

### 2.1 Why Native Windows Execution is Blocked
BindCraft relies on:
- Shell installation scripts (`install_bindcraft.sh`) written for Linux Bash.
- Compiled C++ shared objects (`.so`) for PyRosetta, OpenMM, and Cuda-compiled Jax/PyTorch kernels.
- Linux-specific file path conventions and POSIX signal handling.

Attempting to install BindCraft dependencies directly inside the primary Windows Python virtual environment (`.venv`) would corrupt core dependencies and fail due to missing Windows C++ binaries for PyRosetta.

### 2.2 Recommended Isolation Strategy: Containerized / WSL2 Subprocess Adapter
To preserve the frozen Base V1 core system:

```text
+-----------------------------------------------------------------------+
|  Host OS: Windows 11 (AI Protein Design System Core)                 |
|  - Python 3.11 (.venv)                                                |
|  - SQLite Metadata DB & Artifact Store                                |
|                                                                       |
|  BindCraftGenerator (BaseGenerator Adapter)                           |
|       │                                                               |
|       ├── 1. Prepares target JSON / PDB input                         |
|       ├── 2. Invokes Docker / WSL2 Subprocess Execution               |
|       └── 3. Parses produced CIF/FASTA artifacts & returns Candidates  |
+-----------------------------------│-----------------------------------+
                                    │ CLI / Subprocess Call
+-----------------------------------▼-----------------------------------+
|  Isolated Runtime: WSL2 Ubuntu / Docker Container                     |
|  - Linux Python 3.10 Environment                                      |
|  - CUDA 12.4 / PyTorch / Jax                                          |
|  - PyRosetta + ProteinMPNN + AF2 Model Weights (~5.3 GB)              |
+-----------------------------------------------------------------------+
```

1. **Zero Core Contamination:** Core system communicates strictly via CLI arguments and JSON/FASTA input/output files.
2. **Fallback / Hybrid Mode:** 
   - **Local Mode (Small minibinders, <70 AAs):** Run inside WSL2 Docker container using GPU with low memory flags.
   - **Cloud Offloading Mode (Large targets):** Execute BindCraft container on remote GPU nodes (RunPod / Modal / AWS EC2 g5.xlarge with 24GB VRAM) while storing candidate metadata in local Base V1 DB.

---

## 3. Overall Machine Assessment

**Machine Readiness Status:** **PARTIAL / CLOUD-DEPENDENT**

- **Ready Components:** WSL2, Docker Desktop, CUDA 13.2 driver, local storage (40.4 GB), frozen Core V1 architecture.
- **Hardware Limitations:** 4 GB VRAM is inadequate for medium-to-large target AF2 backpropagation. Local testing is strictly restricted to small minibinders (<60 AAs) or mock/test modes. Production binder design requires remote GPU execution.
