from enum import Enum
import json
from pydantic import BaseModel,Field,ValidationError
from datetime import datetime,timezone


class Severity(str,Enum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"

class EvalMethod(str,Enum):
    RULE_BASED = "rule_based"
    EMBEDDINGS = "embeddings"
    LLM_JUDGE = "llm_judge"
    HUMAN = "human" 

from gel.schema.trace import get_uuid_string
from gel.schema.trace import get_UTC_datetime

class Signal(BaseModel):
    signal_id : str = Field(default_factory = get_uuid_string)
    timestamp : datetime = Field(default_factory = get_UTC_datetime)
    trace_id :str
    evaluator_version : str 
    judge_model : str|None = None
    prompt_version : str|None = None
    score: float = Field(ge=0.0 , le = 1.0)
    confidence :float|None = Field(default = None, ge = 0.0, le= 1.0)
    severity : Severity
    eval_method : EvalMethod
    rubric_breakdown : dict[str, float] = Field(default_factory=dict)
    evidence : list[str] = Field(default_factory=list)
    trace_span_ids : list[str] = Field(default_factory=list)
    known_limitations : str|None = None

if __name__ == "__main__":


    # instance1 = Signal(evaluator_version="1.0.0",score = 0.5,severity=Severity.LOW,eval_method=EvalMethod.HUMAN)
    # print(instance1)
    # raw = instance1.model_dump_json()
    # rebuilt = instance1.model_validate_json(raw)
    # assert rebuilt == instance1, "round trip failed"
    # instance2 = Signal(evaluator_version="1.0.0",score = 0.2,severity=Severity.HIGH,eval_method=EvalMethod.EMBEDDINGS)
    # assert instance1.signal_id != instance2.signal_id, f"the signal id is same of instance1 and instance2"
    # try:
    #     instance3 = Signal(evaluator_version="1.0.0",score = 1.2,severity=Severity.HIGH,eval_method=EvalMethod.EMBEDDINGS)
    #     assert False , "should have raised"
    # except ValidationError as e:
    #     print("score out of range ")
    # try:
    #     instance3 = Signal(evaluator_version="1.0.0",score = 0.2,confidence= 3.5, severity=Severity.HIGH,eval_method=EvalMethod.EMBEDDINGS)
    #     assert False , "should have raised"
    # except ValidationError as e:
    #     print("confidence out of range ")
    # assert rebuilt.severity == Severity.LOW, "enum did not survive"
    # print("all tests passed")

    breakdown = {"relevance": 0.8}
    evidence=["span one"]
    trace_span_ids=["step-1"]
    known_limitations = "none known"
    inst= Signal(evaluator_version="1.0.0",score = 0.9, confidence= 0.7, severity=Severity.LOW,eval_method = EvalMethod.HUMAN,rubric_breakdown=breakdown,evidence= evidence,known_limitations=known_limitations,trace_span_ids=trace_span_ids)
    a= Signal(evaluator_version="1.0.0",score = 0.9, confidence= 0.7, severity=Severity.LOW,eval_method = EvalMethod.HUMAN,known_limitations=known_limitations)
    b= Signal(evaluator_version="1.0.0",score = 0.9, confidence= 0.7, severity=Severity.LOW ,eval_method = EvalMethod.HUMAN,known_limitations=known_limitations)
    raw = inst.model_dump_json()
    rebuilt = Signal.model_validate_json(raw)
    assert rebuilt.rubric_breakdown == breakdown,"rubric_breakdown did not match"
    assert rebuilt.evidence == evidence,"evidence did not match"
    assert rebuilt.trace_span_ids == trace_span_ids,"trace_span_ids did not match"
    assert a.evidence is not b.evidence, "a and b shares the list"
    print("end of tests")

