import json

from gel.groundedness.llm_output import strip_code_fences
from gel.groundedness.models import Claim, ClaimVerdict, EntailmentLabel, EvidenceSpan
from gel.providers.call_llm import call_llm

PROMPT_VERSION = "entailment-v1"


def parse_verdict(raw: str) -> tuple[EntailmentLabel, str]:
    text = strip_code_fences(raw)
    data = json.loads(text)

    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object, got {type(data).__name__}")

    label_raw = data.get("label")
    if not isinstance(label_raw, str):
        raise ValueError("Missing or non-string 'label' field")

    label = EntailmentLabel(label_raw)

    reason_raw = data.get("reason", "")
    if reason_raw is None:
        reason = ""
    elif isinstance(reason_raw, str):
        reason = reason_raw.strip()
    else:
        raise ValueError(f"Expected string 'reason' field, got {type(reason_raw).__name__}")

    return label, reason


def build_entailment_prompt(claim_text: str, evidence: list[EvidenceSpan]) -> str:
    bullets = "\n".join(f"- {span.text}" for span in evidence)
    return f"""Decide whether the EVIDENCE supports the CLAIM.

Labels:
- entailed: the evidence clearly states or directly implies the claim.
- contradicted: the evidence states the opposite of the claim.
- not_enough_info: the evidence neither confirms nor contradicts the claim.

Use ONLY the evidence. Do not use outside knowledge.
Return ONLY a JSON object: {{"label": "<label>", "reason": "<one short sentence>"}}

CLAIM:
{claim_text}

EVIDENCE:
{bullets}"""


def check_entailment(
    claim: Claim,
    evidence: list[EvidenceSpan],
    provider: str = "gemini",
    model: str = "gemini-3.5-flash-lite",
) -> ClaimVerdict:
    if not evidence:
        return ClaimVerdict(
            claim=claim,
            label=EntailmentLabel.NOT_ENOUGH_INFO,
            reason="No evidence retrieved",
            evidence=[],
        )

    prompt = build_entailment_prompt(claim.text, evidence)
    raw = call_llm(provider, model, prompt)
    label, reason = parse_verdict(raw)
    return ClaimVerdict(
        claim=claim,
        label=label,
        reason=reason,
        evidence=evidence,
    )

if __name__ == "__main__":
    from gel.groundedness.models import Claim, EvidenceSpan, EntailmentLabel as L
    ev = [EvidenceSpan(doc_id="d1", text="Paris is the capital of France.", similarity=0.9),
          EvidenceSpan(doc_id="d1", text="It sits on the Seine river.", similarity=0.4)]

    p = build_entailment_prompt("Paris is in France.", ev)
    assert "Paris is in France." in p and "- Paris is the capital of France." in p and '"label"' in p

    # no evidence: no LLM call, even with the mock provider
    v = check_entailment(Claim(text="Anything."), [], provider="mock", model="mock")
    assert v.label == L.NOT_ENOUGH_INFO and v.evidence == []

    # mock echoes the prompt (not JSON), so parsing must fail loudly
    try:
        check_entailment(Claim(text="Paris is in France."), ev, provider="mock", model="mock")
        assert False, "should have raised"
    except ValueError:
        pass

    # live calls (3, cached afterwards)
    assert check_entailment(Claim(text="Paris is the capital of France."), ev).label == L.ENTAILED
    assert check_entailment(Claim(text="Paris is the capital of Germany."), ev).label == L.CONTRADICTED
    assert check_entailment(Claim(text="Paris has two million residents."), ev).label == L.NOT_ENOUGH_INFO
    print("check_entailment tests passed")