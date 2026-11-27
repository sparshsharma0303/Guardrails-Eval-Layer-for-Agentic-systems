from gel.groundedness import claim_extraction, entailment
from gel.groundedness.claim_extraction import (
    compute_extraction_confidence,
    extract_claims,
)
from gel.groundedness.entailment import check_entailment
from gel.groundedness.evidence_retrieval import retrieve_evidence
from gel.groundedness.metrics import (
    compute_metrics,
    groundedness_score,
    groundedness_severity,
)
from gel.groundedness.models import ClaimVerdict, EntailmentLabel
from gel.schema.eval_signal import EvalMethod, Signal
from gel.schema.trace import RetrievedDocument

EVALUATOR_VERSION = "1.0.0"


def evaluate_groundedness(
    answer: str,
    documents: list[RetrievedDocument],
    trace_id: str,
    trace_span_ids: list[str],
    source_step_id: str | None = None,
    provider: str = "gemini",
    model: str = "gemini-3.5-flash-lite",
    top_k: int = 2,
) -> Signal:
    claims = extract_claims(answer, source_step_id, provider, model)

    verdicts: list[ClaimVerdict] = []
    for claim in claims:
        evidence = retrieve_evidence(claim.text, documents, top_k=top_k)
        verdict = check_entailment(claim, evidence, provider, model)
        verdicts.append(verdict)

    conf = compute_extraction_confidence(answer, claims)
    metrics = compute_metrics(verdicts, conf)

    evidence_strings: list[str] = []
    for verdict in verdicts:
        if verdict.label == EntailmentLabel.ENTAILED:
            continue
        if not verdict.evidence:
            entry = f"[no evidence] {verdict.claim.text}"
        else:
            best_span = verdict.evidence[0].text
            entry = (
                f"[{verdict.label.value}] {verdict.claim.text} "
                f"| evidence: {best_span} | {verdict.reason}"
            )
        evidence_strings.append(entry[:300])
        if len(evidence_strings) == 10:
            break

    return Signal(
        score=groundedness_score(verdicts),
        severity=groundedness_severity(metrics),
        eval_method=EvalMethod.LLM_JUDGE,
        judge_model=model,
        prompt_version=f"{claim_extraction.PROMPT_VERSION}+{entailment.PROMPT_VERSION}",
        evaluator_version=EVALUATOR_VERSION,
        rubric_breakdown={k: float(v) for k, v in metrics.model_dump().items()},
        confidence=metrics.claim_extraction_confidence,
        evidence=evidence_strings,
        known_limitations=(
            "LLM entailment can err; retrieval is sentence-level embedding similarity "
            "and may miss evidence spread across sentences; extraction confidence is a "
            "proxy that checks claims against the answer's wording."
        ),
        trace_id=trace_id,
        trace_span_ids=trace_span_ids,
    )

from gel.schema.trace import AgentMessageStep, RetrievalStep, RetrievedDocument, Trace


def evaluate_trace_groundedness(
    trace: Trace,
    provider: str = "gemini",
    model: str = "gemini-3.5-flash-lite",
) -> Signal | None:
    final_steps = [
        step
        for step in trace.steps
        if isinstance(step, AgentMessageStep) and step.is_final_answer
    ]
    if not final_steps:
        return None
    final = final_steps[-1]

    retrieval_steps = [
        step for step in trace.steps if isinstance(step, RetrievalStep)
    ]
    if not retrieval_steps:
        return None

    docs: list[RetrievedDocument] = [
        doc for step in retrieval_steps for doc in step.retrieved_documents
    ]
    span_ids = [step.step_id for step in retrieval_steps] + [final.step_id]

    return evaluate_groundedness(
        final.content,
        docs,
        trace.metadata.trace_id,
        span_ids,
        source_step_id=final.step_id,
        provider=provider,
        model=model,
    )


if __name__ == "__main__":
    from gel.schema.eval_signal import Severity, Signal
    from gel.schema.trace import RetrievedDocument

    docs = [
        RetrievedDocument(
            doc_id="d1",
            content="Paris is the capital of France. It sits on the Seine river.",
        ),
        RetrievedDocument(
            doc_id="d2",
            content="The stock market closed lower on Friday. Oil prices rose.",
        ),
    ]

    good = evaluate_groundedness("Paris is the capital of France.", docs, "t-1", ["s-1"])
    assert good.rubric_breakdown["num_contradicted_claims"] == 0.0
    assert good.severity in (Severity.INFORMATIONAL, Severity.LOW) and good.score >= 0.5

    bad = evaluate_groundedness("Paris is the capital of Germany.", docs, "t-1", ["s-1"])
    assert bad.rubric_breakdown["num_contradicted_claims"] >= 1.0
    assert bad.severity == Severity.HIGH and bad.score == 0.0 and bad.evidence

    print(good.severity, good.score, "|", bad.severity, bad.score)
    print(bad.evidence)
    assert Signal.model_validate_json(bad.model_dump_json()) == bad
    print("evaluate_groundedness tests passed")