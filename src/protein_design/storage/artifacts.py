"""Filesystem artifact store for candidate files (FASTA, CIF, PDB, logs).

Artifact directory layout:
    candidates/
    └── {target_id}/
        └── {candidate_id}/
            ├── sequence.fasta
            ├── binder.cif
            ├── complex.cif
            ├── provenance.json
            └── artifacts/
                ├── generation_log.json
                ├── prediction_output/
                └── validation_results/
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from protein_design.schemas import Candidate, Target
from protein_design.logging import get_logger

log = get_logger(module="storage.artifacts")


class ArtifactStore:
    """Filesystem-based artifact storage.

    Organizes candidate files in a predictable directory hierarchy.
    Each candidate gets its own directory under its target.
    """

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def candidate_dir(self, target_id: str, candidate_id: str) -> Path:
        """Get the artifact directory for a candidate."""
        d = self.base_dir / target_id / candidate_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_sequence(
        self,
        target_id: str,
        candidate_id: str,
        sequence: str,
        description: str = "",
    ) -> Path:
        """Save a candidate sequence as FASTA."""
        d = self.candidate_dir(target_id, candidate_id)
        fasta_path = d / "sequence.fasta"
        header = f">{candidate_id}"
        if description:
            header += f" {description}"
        fasta_path.write_text(f"{header}\n{sequence}\n", encoding="utf-8")
        log.debug("sequence_saved", candidate_id=candidate_id, path=str(fasta_path))
        return fasta_path

    def save_structure(
        self,
        target_id: str,
        candidate_id: str,
        content: str,
        filename: str = "binder.cif",
    ) -> Path:
        """Save a structure file (CIF or PDB)."""
        d = self.candidate_dir(target_id, candidate_id)
        structure_path = d / filename
        structure_path.write_text(content, encoding="utf-8")
        log.debug("structure_saved", candidate_id=candidate_id, path=str(structure_path))
        return structure_path

    def save_provenance(
        self,
        target_id: str,
        candidate_id: str,
        provenance: dict[str, Any],
    ) -> Path:
        """Save provenance record as JSON."""
        d = self.candidate_dir(target_id, candidate_id)
        prov_path = d / "provenance.json"
        prov_path.write_text(
            json.dumps(provenance, indent=2, default=str),
            encoding="utf-8",
        )
        return prov_path

    def save_artifact(
        self,
        target_id: str,
        candidate_id: str,
        filename: str,
        content: str | bytes,
        subdir: str = "artifacts",
    ) -> Path:
        """Save an arbitrary artifact file."""
        d = self.candidate_dir(target_id, candidate_id) / subdir
        d.mkdir(parents=True, exist_ok=True)
        artifact_path = d / filename
        if isinstance(content, bytes):
            artifact_path.write_bytes(content)
        else:
            artifact_path.write_text(content, encoding="utf-8")
        return artifact_path

    def get_candidate_files(self, target_id: str, candidate_id: str) -> list[Path]:
        """List all files in a candidate's artifact directory."""
        d = self.candidate_dir(target_id, candidate_id)
        if not d.exists():
            return []
        return sorted(d.rglob("*"))

    def candidate_artifact_exists(
        self,
        target_id: str,
        candidate_id: str,
        filename: str,
    ) -> bool:
        """Check if a specific artifact exists for a candidate."""
        d = self.base_dir / target_id / candidate_id
        return (d / filename).exists()
