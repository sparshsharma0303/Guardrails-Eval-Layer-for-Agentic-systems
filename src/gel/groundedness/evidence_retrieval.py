
import re


def split_into_spans(text: str) -> list[str]:
    # limitation: abbreviations like "Dr. Smith" will split on the period.
    parts = re.split(r"(?<=[.!?])\s+|[\r\n]+", text)
    return [part.strip() for part in parts if part.strip()]



if __name__ == "__main__":
    assert split_into_spans("Paris is the capital. It is big!  Is it old?") == ["Paris is the capital.", "It is big!", "Is it old?"]
    assert split_into_spans("Line one\nLine two.") == ["Line one", "Line two."]
    assert split_into_spans("No punctuation") == ["No punctuation"]
    assert split_into_spans("   ") == []
    from gel.groundedness.models import EvidenceSpan
    s = EvidenceSpan(doc_id="d1", text="Paris is the capital.", similarity=0.8)
    assert EvidenceSpan.model_validate_json(s.model_dump_json()) == s
    print("split_into_spans tests passed")