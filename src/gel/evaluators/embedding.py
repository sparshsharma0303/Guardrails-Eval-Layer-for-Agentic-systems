# src/gel/evaluators/embedding.py
import math
from collections.abc import Sequence
from sentence_transformers import SentenceTransformer
from gel.schema.eval_signal import Signal,Severity,EvalMethod


MODEL_NAME = "all-MiniLM-L6-v2"
_model: SentenceTransformer | None = None

def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"Vector dimensions must match: got {len(a)} and {len(b)}")

    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return dot_product / (norm_a * norm_b)

def embed_text(text: str) -> list[float]:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model.encode(text).tolist()


EVALUATOR_VERSION = "1.0.0"


def run_embedding_check(
    reference: str,
    candidate: str,
    trace_id: str,
    trace_span_ids: list[str],
    threshold: float = 0.5,
) -> Signal:
    raw_cosine = cosine_similarity(embed_text(reference), embed_text(candidate))
    score = max(0.0, min(1.0, raw_cosine))

    if score >= threshold:
        severity = Severity.INFORMATIONAL
        evidence = []
    else:
        severity = Severity.MEDIUM
        evidence = [f"reference: {reference[:200]}", f"candidate: {candidate[:200]}"]

    return Signal(
        score=score,
        severity=severity,
        eval_method=EvalMethod.EMBEDDINGS,
        evaluator_version=EVALUATOR_VERSION,
        rubric_breakdown={"semantic_similarity": raw_cosine},
        evidence=evidence,
        trace_id=trace_id,
        trace_span_ids=trace_span_ids,
        confidence=None,
        known_limitations=(
            "Measures semantic closeness, not factual support; "
            "cannot detect negation or contradiction."
        ),
        judge_model=None,
        prompt_version=None,
    )

if __name__ == "__main__":
    from gel.schema.eval_signal import Signal, Severity, EvalMethod
    ok = run_embedding_check("The cat sat on the mat.", "A kitten is resting on a rug.", "t-1", ["s-1"])
    bad = run_embedding_check("The cat sat on the mat.", "Quarterly revenue grew by twelve percent.", "t-1", ["s-1"])
    assert ok.severity == Severity.INFORMATIONAL and ok.evidence == []
    assert bad.severity == Severity.MEDIUM and len(bad.evidence) == 2
    assert 0.0 <= bad.score <= 1.0 and bad.rubric_breakdown["semantic_similarity"] < 0.0
    assert ok.eval_method == EvalMethod.EMBEDDINGS and ok.confidence is None
    assert Signal.model_validate_json(bad.model_dump_json()) == bad
    print("run_embedding_check tests passed")