"""Unit tests for ESMFold + ipSAE score provenance and availability gates."""

from __future__ import annotations

from protein_design.predictors.esmfold_ipsae import (
    ESMFold2_ipSAE_Scorer,
    compute_ipsae_score,
)
from protein_design.schemas import (
    Candidate,
    CandidateStatus,
    ScientificStatus,
    ScoreProvenance,
    Target,
)


def test_compute_ipsae_score_with_missing_inputs_returns_none() -> None:
    # Missing pLDDT or interface PAE must return None rather than fabricating numbers
    assert compute_ipsae_score(plddt=None, interface_pae=10.0) is None
    assert compute_ipsae_score(plddt=80.0, interface_pae=None) is None
    # Zero valid contacts returns 0.0
    assert compute_ipsae_score(plddt=80.0, interface_pae=8.0, interface_contacts=0) == 0.0


def test_esmfold_predictor_tags_proxy_provenance() -> None:
    scorer = ESMFold2_ipSAE_Scorer()
    target = Target(target_id="EGFR", name="EGFR", source="test", sequence="MKTVRQERLK")
    candidate = Candidate(
        candidate_id="cand_test_001",
        target_id="EGFR",
        sequence="EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKDRLSGHYWGQGTLVTVSS",
        status=CandidateStatus.GENERATED,
        scientific_status=ScientificStatus.GENERATED,
    )

    result = scorer.predict(candidate, target, config={})
    assert result.score_provenance == ScoreProvenance.HEURISTIC_PROXY.value
    assert result.metrics["score_provenance"] == ScoreProvenance.HEURISTIC_PROXY.value
    assert result.metrics["is_model_predicted"] is False
    assert result.metrics["is_experimentally_validated"] is False
    assert result.confidence is not None


def test_esmfold_predictor_strict_real_model_returns_unavailable() -> None:
    scorer = ESMFold2_ipSAE_Scorer(require_real_model=True)
    target = Target(target_id="EGFR", name="EGFR", source="test", sequence="MKTVRQERLK")
    candidate = Candidate(
        candidate_id="cand_test_002",
        target_id="EGFR",
        sequence="EVQLVESGGGLVQPGGSLRLSCAASGFTFSSYAMSWVRQAPGKGLEWVSAISGSGGSTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCAKDRLSGHYWGQGTLVTVSS",
        status=CandidateStatus.GENERATED,
        scientific_status=ScientificStatus.GENERATED,
    )

    result = scorer.predict(candidate, target, config={})
    assert result.score_provenance == ScoreProvenance.UNVERIFIED.value
    assert result.confidence is None
    assert result.metrics["ipsae_score"] is None
    assert result.metrics["score_status"] == "UNAVAILABLE"
