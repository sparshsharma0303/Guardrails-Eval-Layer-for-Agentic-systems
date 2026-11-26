from gel.groundedness.models import ClaimVerdict, GroundednessMetrics, EvidenceSpan, Claim, EntailmentLabel 
from gel.schema.eval_signal import Severity

def groundedness_score(verdicts: list[ClaimVerdict]) -> float:
    if not verdicts:
        return 0.0
    entailed_count = sum(1 for v in verdicts if v.label == EntailmentLabel.ENTAILED)
    return entailed_count / len(verdicts)

def groundedness_severity(metrics: GroundednessMetrics) -> Severity:
    if metrics.num_contradicted_claims >= 1:
        return Severity.HIGH
    if metrics.num_claims == 0:
        return Severity.MEDIUM
    if metrics.retrieval_failure_rate >= 0.5 or metrics.num_unsupported_claims / metrics.num_claims >= 0.3:
        return Severity.MEDIUM
    if metrics.num_unsupported_claims >= 1 or metrics.retrieval_failure_rate > 0 or metrics.claim_extraction_confidence < 0.4:
        return Severity.LOW
    return Severity.INFORMATIONAL


def compute_metrics(
    verdicts: list[ClaimVerdict],
    claim_extraction_confidence: float,
) -> GroundednessMetrics:
    num_claims = len(verdicts)

    if num_claims == 0:
        return GroundednessMetrics(
            num_claims=0,
            num_unsupported_claims=0,
            num_contradicted_claims=0,
            evidence_coverage=0.0,
            retrieval_failure_rate=0.0,
            claim_extraction_confidence=claim_extraction_confidence,
        )

    num_contradicted_claims = sum(
        1 for v in verdicts if v.label == EntailmentLabel.CONTRADICTED
    )
    num_unsupported_claims = sum(
        1
        for v in verdicts
        if v.label == EntailmentLabel.NOT_ENOUGH_INFO and len(v.evidence) > 0
    )
    claims_with_evidence = sum(1 for v in verdicts if len(v.evidence) > 0)
    claims_without_evidence = num_claims - claims_with_evidence

    return GroundednessMetrics(
        num_claims=num_claims,
        num_unsupported_claims=num_unsupported_claims,
        num_contradicted_claims=num_contradicted_claims,
        evidence_coverage=claims_with_evidence / num_claims,
        retrieval_failure_rate=claims_without_evidence / num_claims,
        claim_extraction_confidence=claim_extraction_confidence,
    )
if __name__ == "__main__":
    from gel.groundedness.models import Claim, ClaimVerdict, EvidenceSpan, EntailmentLabel as L
    ev = [EvidenceSpan(doc_id="d1", text="x", similarity=0.9)]
    verdicts = [
        ClaimVerdict(claim=Claim(text="a"), label=L.ENTAILED, evidence=ev),
        ClaimVerdict(claim=Claim(text="b"), label=L.CONTRADICTED, evidence=ev),
        ClaimVerdict(claim=Claim(text="c"), label=L.NOT_ENOUGH_INFO, evidence=ev),
        ClaimVerdict(claim=Claim(text="d"), label=L.NOT_ENOUGH_INFO, evidence=[]),
    ]
    m = compute_metrics(verdicts, claim_extraction_confidence=0.9)
    assert m.num_claims == 4
    assert m.num_contradicted_claims == 1
    assert m.num_unsupported_claims == 1          # "d" has no evidence, so it is a retrieval failure
    assert m.evidence_coverage == 0.75 and m.retrieval_failure_rate == 0.25
    assert m.claim_extraction_confidence == 0.9

    empty = compute_metrics([], claim_extraction_confidence=0.5)
    assert empty.num_claims == 0 and empty.evidence_coverage == 0.0 and empty.retrieval_failure_rate == 0.0
    print("compute_metrics tests passed")

    from gel.schema.eval_signal import Severity as S
    def M(n, un, co, cov, fail, conf):
        return GroundednessMetrics(num_claims=n, num_unsupported_claims=un, num_contradicted_claims=co,
                                evidence_coverage=cov, retrieval_failure_rate=fail,
                                claim_extraction_confidence=conf)
    assert groundedness_severity(M(4, 0, 1, 1.0, 0.0, 0.9)) == S.HIGH
    assert groundedness_severity(M(0, 0, 0, 0.0, 0.0, 0.9)) == S.MEDIUM
    assert groundedness_severity(M(4, 0, 0, 0.5, 0.5, 0.9)) == S.MEDIUM
    assert groundedness_severity(M(10, 3, 0, 1.0, 0.0, 0.9)) == S.MEDIUM
    assert groundedness_severity(M(10, 1, 0, 1.0, 0.0, 0.9)) == S.LOW
    assert groundedness_severity(M(4, 0, 0, 0.75, 0.25, 0.9)) == S.LOW
    assert groundedness_severity(M(4, 0, 0, 1.0, 0.0, 0.2)) == S.LOW
    assert groundedness_severity(M(4, 0, 0, 1.0, 0.0, 0.9)) == S.INFORMATIONAL

    ev = [EvidenceSpan(doc_id="d1", text="x", similarity=0.9)]
    vs = [ClaimVerdict(claim=Claim(text=t), label=l, evidence=ev) for t, l in
        [("a", L.ENTAILED), ("b", L.ENTAILED), ("c", L.CONTRADICTED), ("d", L.NOT_ENOUGH_INFO)]]
    assert groundedness_score(vs) == 0.5 and groundedness_score([]) == 0.0
    assert groundedness_score(vs[:2]) == 1.0
    print("score and severity tests passed")