"""Unit tests for VHH generator target-salted seeding, diversity, and reproducibility."""

from __future__ import annotations

from protein_design.generators.vhh import VHHScaffoldGenerator
from protein_design.schemas import Target


def test_vhh_generator_intra_target_deterministic_reproducibility() -> None:
    generator = VHHScaffoldGenerator()
    target = Target(target_id="TNF-alpha", name="TNF-alpha", source="test", sequence="MSTESMIRDVELA")

    run1 = generator.generate(target, config={}, num_candidates=5, seed=42)
    run2 = generator.generate(target, config={}, num_candidates=5, seed=42)

    assert len(run1) == 5
    assert len(run2) == 5
    for c1, c2 in zip(run1, run2, strict=True):
        assert c1.sequence == c2.sequence
        assert c1.seed == c2.seed


def test_vhh_generator_inter_target_collision_prevention() -> None:
    """Verify that targets (TNF-alpha, TfR1, TNFR1) do not produce colliding sequences under same base seed."""
    generator = VHHScaffoldGenerator()

    t_tnf = Target(target_id="TNF-alpha", name="TNF-alpha", source="test", sequence="MSTESMIRDVELA")
    t_tfr1 = Target(target_id="TfR1", name="TfR1", source="test", sequence="MMDQARSAFSNL")
    t_tnfr1 = Target(target_id="TNFR1", name="TNFR1", source="test", sequence="MGLSTVPDLLLP")

    cands_tnf = generator.generate(t_tnf, config={}, num_candidates=5, seed=42)
    cands_tfr1 = generator.generate(t_tfr1, config={}, num_candidates=5, seed=42)
    cands_tnfr1 = generator.generate(t_tnfr1, config={}, num_candidates=5, seed=42)

    seqs_tnf = {c.sequence for c in cands_tnf}
    seqs_tfr1 = {c.sequence for c in cands_tfr1}
    seqs_tnfr1 = {c.sequence for c in cands_tnfr1}

    # Inter-target collisions must be 0
    assert len(seqs_tnf.intersection(seqs_tfr1)) == 0
    assert len(seqs_tnf.intersection(seqs_tnfr1)) == 0
    assert len(seqs_tfr1.intersection(seqs_tnfr1)) == 0

    # Within-target diversity must be 100% (5 unique sequences per target)
    assert len(seqs_tnf) == 5
    assert len(seqs_tfr1) == 5
    assert len(seqs_tnfr1) == 5
