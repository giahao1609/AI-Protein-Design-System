# Terminology — AI Protein Design System

## Core Terms

| Term | Definition |
|------|-----------|
| **Target** | The protein that binders are designed to bind to |
| **Candidate** | A designed protein (binder) that may bind the target |
| **Binder** | A protein that binds to a target. Only confirmed after experimental validation |
| **Minibinder** | A small designed protein (typically 40-80 residues) that binds a target |
| **VHH / Nanobody** | A single-domain antibody fragment (~120 residues) |
| **De novo** | Designed from scratch, not derived from a natural protein |

## Pipeline Terms

| Term | Definition |
|------|-----------|
| **Generator** | A model/tool that produces candidate protein sequences |
| **Predictor** | A model/tool that predicts 3D structure of a protein |
| **Validator** | A tool that checks quality/validity of a candidate |
| **Pipeline** | The full workflow from target to validated candidates |
| **ExperimentRun** | A single execution of the pipeline with specific config |

## Scientific Terms

| Term | Definition |
|------|-----------|
| **pLDDT** | Predicted Local Distance Difference Test (structure confidence) |
| **pTM** | Predicted Template Modeling score (global fold quality) |
| **ipTM** | Interface predicted TM-score (complex interface quality) |
| **pAE** | Predicted Aligned Error (inter-residue distance uncertainty) |
| **RMSD** | Root Mean Square Deviation (structural similarity) |

## Status Terms

| Term | Definition |
|------|-----------|
| **GENERATED** | Candidate was produced by a model. No validation. |
| **COMPUTATIONALLY_VALIDATED** | Passed computational quality checks |
| **EXPERIMENTALLY_TESTED** | Wet-lab experiment was performed |
| **EXPERIMENTALLY_VALIDATED** | Wet-lab result confirms the claim |

## ⚠️ Forbidden Terms (Without Evidence)

These terms MUST NOT be used to describe candidates based solely on AI predictions:
- "functional"
- "successful"
- "validated" (without "computationally" qualifier)
- "binds strongly"
- "high-affinity" (without experimental measurement)
