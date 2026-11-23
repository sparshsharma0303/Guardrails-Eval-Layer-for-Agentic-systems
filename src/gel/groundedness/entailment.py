import json

from gel.groundedness.llm_output import strip_code_fences
from gel.groundedness.models import EntailmentLabel


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


if __name__ == "__main__":
    from gel.groundedness.models import EntailmentLabel as L
    assert parse_verdict('{"label": "entailed", "reason": "stated directly"}') == (L.ENTAILED, "stated directly")
    assert parse_verdict('```json\n{"label": "contradicted"}\n```') == (L.CONTRADICTED, "")
    assert parse_verdict('{"label": "not_enough_info", "reason": "x"}')[0] == L.NOT_ENOUGH_INFO
    for bad in ["not json", '["entailed"]', '{"reason": "x"}', '{"label": "maybe"}']:
        try:
            parse_verdict(bad)
            assert False, f"should have raised for {bad!r}"
        except ValueError:
            pass
    from gel.groundedness.llm_output import strip_code_fences
    assert strip_code_fences('```json\n[1]\n```') == "[1]" and strip_code_fences("  [1] ") == "[1]"
    print("parse_verdict tests passed")