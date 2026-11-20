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

class EvidenceSpan(BaseModel):
    doc_id:str
    text: str
    similarity: float
    


if __name__ == "__main__":
    claim = Claim(text="Paris is the capital of France.", source_step_id="step-1")
    restored = Claim.model_validate_json(claim.model_dump_json())
    assert restored == claim

    try:
        EntailmentLabel("maybe")
        assert False, "Expected ValueError for invalid EntailmentLabel"
    except ValueError:
        pass

    print("models.py tests passed!")