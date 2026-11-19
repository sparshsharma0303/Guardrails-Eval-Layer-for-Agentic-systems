import json
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


def get_uuid_string() -> str:
    return str(uuid4())


class EntailmentLabel(str, Enum):
    ENTAILED = "entailed"
    CONTRADICTED = "contradicted"
    NOT_ENOUGH_INFO = "not_enough_info"


class Claim(BaseModel):
    claim_id: str = Field(default_factory=get_uuid_string)
    text: str
    source_step_id: str | None = None




def parse_claims(raw: str) -> list[str]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

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