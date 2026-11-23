import json

from gel.groundedness.models import Claim
from gel.groundedness.llm_output import strip_code_fences

from gel.providers.call_llm import call_llm
from pydantic import BaseModel, Field

from gel.evaluators.embedding import cosine_similarity, embed_text
from gel.groundedness.evidence_retrieval import split_into_spans
from gel.groundedness.models import Claim


def compute_extraction_confidence(answer: str, claims: list[Claim]) -> float:
    if not claims:
        return 0.0

    spans = split_into_spans(answer)
    if not spans:
        return 0.0

    span_embeddings = [embed_text(span) for span in spans]

    best_scores: list[float] = []
    for claim in claims:
        claim_embedding = embed_text(claim.text)
        raw_best = max(
            cosine_similarity(claim_embedding, span_emb)
            for span_emb in span_embeddings
        )
        clamped = max(0.0, min(1.0, raw_best))
        best_scores.append(clamped)

    return sum(best_scores) / len(best_scores)


def parse_claims(raw: str) -> list[str]:
    text = strip_code_fences(raw)
    data = json.loads(text)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list of claims, got {type(data).__name__}")

    claims: list[str] = []
    for item in data:
        if not isinstance(item, str):
            raise ValueError(
                f"Expected string items in claims list, got {type(item).__name__}"
            )
        cleaned = item.strip()
        if cleaned:
            claims.append(cleaned)

    return claims


def build_extraction_prompt(answer: str) -> str:
    return f"""Decompose the ANSWER below into atomic factual claims.

Rules:
- Each claim states exactly one fact and can be understood on its own.
- Replace pronouns with the thing they refer to.
- Skip opinions, questions, greetings and hedging.
- Return ONLY a JSON array of strings. No commentary, no markdown.

ANSWER:
{answer}"""


def extract_claims(answer: str, source_step_id: str | None = None, provider: str = "gemini", model: str = "gemini-3.5-flash-lite",) -> list[Claim]:
    prompt = build_extraction_prompt(answer)
    response = call_llm(provider, model, prompt)
    claim_texts = parse_claims(response)
    return [Claim(text=text, source_step_id=source_step_id) for text in claim_texts]

if __name__ == "__main__":
    assert parse_claims('["A.", "B."]') == ["A.", "B."]
    assert parse_claims('```json\n["A.", "B."]\n```') == ["A.", "B."]
    assert parse_claims('["  A.  ", "", "B."]') == ["A.", "B."]
    for bad in ["not json", '{"claims": ["A."]}', '["A.", 5]']:
        try:
            parse_claims(bad)
            assert False, f"should have raised for {bad!r}"
        except ValueError:
            pass
    print("parse_claims tests passed")
    prompt = build_extraction_prompt("Paris is the capital of France.")
    assert "Paris is the capital of France." in prompt and "JSON" in prompt

    try:
        extract_claims("Paris is the capital of France.", provider="mock", model="mock")
        assert False, "should have raised"
    except ValueError:
        pass

    answer = "Paris is the capital of France and has about two million residents."
    claims = extract_claims(answer, source_step_id="step-9")
    print([c.text for c in claims])
    assert len(claims) >= 2 and all(c.source_step_id == "step-9" for c in claims)
    print("extract_claims tests passed")

    from gel.groundedness.models import Claim
    ans = "Paris is the capital of France and has about two million residents."
    good = [Claim(text="Paris is the capital of France."), Claim(text="Paris has about two million residents.")]
    bad = [Claim(text="The moon is made of cheese.")]
    mixed = good + bad

    c_good = compute_extraction_confidence(ans, good)
    c_bad = compute_extraction_confidence(ans, bad)
    c_mixed = compute_extraction_confidence(ans, mixed)
    print(f"good={c_good:.3f} bad={c_bad:.3f} mixed={c_mixed:.3f}")
    assert c_good >= 0.5 and c_bad < 0.3
    assert c_bad < c_mixed < c_good
    assert compute_extraction_confidence(ans, []) == 0.0 and compute_extraction_confidence("", good) == 0.0
    print("extraction confidence tests passed")