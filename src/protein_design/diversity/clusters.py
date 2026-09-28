"""Diversity clustering — Schema and utilities for diversity analysis.

BASE V1 defines the schema for diversity clusters but defers
actual clustering implementations (e.g., MMseqs2, Foldseek)
to future model integration phases.
"""

from __future__ import annotations

from typing import Any, Optional

from protein_design.schemas.common import DiversityInfo, hash_string


def compute_sequence_identity(seq1: str, seq2: str) -> float:
    """Compute pairwise sequence identity (simple, no alignment).

    This is a basic identity metric. For production use,
    integrate proper alignment tools (BLAST, MMseqs2).
    """
    if not seq1 or not seq2:
        return 0.0
    min_len = min(len(seq1), len(seq2))
    max_len = max(len(seq1), len(seq2))
    if max_len == 0:
        return 0.0
    matches = sum(a == b for a, b in zip(seq1[:min_len], seq2[:min_len]))
    return matches / max_len


def assign_diversity_info(
    generator_family: str,
    sequence_cluster: Optional[str] = None,
    structure_cluster: Optional[str] = None,
    interface_cluster: Optional[str] = None,
    binding_mode_cluster: Optional[str] = None,
) -> DiversityInfo:
    """Create a DiversityInfo record.

    In BASE V1, only generator_family is populated.
    Cluster IDs will be assigned by clustering tools in later phases.
    """
    return DiversityInfo(
        sequence_cluster=sequence_cluster,
        structure_cluster=structure_cluster,
        interface_cluster=interface_cluster,
        binding_mode_cluster=binding_mode_cluster,
        generator_family=generator_family,
    )
