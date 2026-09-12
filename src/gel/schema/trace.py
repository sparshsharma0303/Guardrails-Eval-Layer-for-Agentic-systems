from pydantic import BaseModel,Field
from datetime import datetime,timezone
from uuid import uuid4
from enum import Enum
from typing import Literal,Any,Annotated,Union

def get_uuid_string():
    return str(uuid4())

def get_UTC_datetime():
    return datetime.now(timezone.utc)

class TraceMetaData(BaseModel):
    trace_id: str = Field(default_factory = get_uuid_string)
    agent_id:str
    agent_role: str
    framework:str
    created_at: datetime =  Field(default_factory = get_UTC_datetime)
    schema_version: str = "1.0.0"
    framework_version: str | None = None
    adapter_version:str | None = None
    redaction_applied:bool = False
    redaction_filter_version:str | None = None

class StepStatus(str,Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"

class StepBase(BaseModel):
    step_id:str = Field(default_factory=get_uuid_string)
    step_index:int
    timestamp_start:datetime
    timestamp_end: datetime | None = None
    status: StepStatus = StepStatus.SUCCESS
    retry_count :int = 0 
    cache_hit:bool = False
    redacted:bool = False
    parent_step_id : str|None = None
    latency_ms: float  | None = None
    was_rate_limited: bool = False
    error_type :str| None = None
    error_message: str | None = None
    cache_key:str| None = None
    framework_metadata : dict = Field(default_factory=dict)
    
class UserMessageStep(StepBase):
    step_type: Literal["user_message"] = "user_message"
    content :str

class AgentMessageStep(StepBase):
    step_type: Literal["agent_message"] = "agent_message"
    content: str
    is_final_answer: bool = False

class ToolCallStep(StepBase):
    step_type: Literal["tool_call"] = "tool_call"
    tool_name:str
    tool_args:dict 
    tool_result: Any = None

class RetrievedDocument(BaseModel):
    doc_id: str 
    content: str
    source: str | None = None
    score: float | None = None

class RetrievalStep(StepBase):
    step_type: Literal["retrieval"] = "retrieval"
    query: str
    retrieved_documents : list[RetrievedDocument] = Field(default_factory=list) 

class TokenUsage(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens :int | None = None 
    total_tokens : int | None = None

class LLMCallStep(StepBase):
    step_type: Literal["llm_call"] = "llm_call"
    provider : str
    model : str
    prompt: str
    prompt_version: str |None = None
    completion: str | None = None
    token_usage: TokenUsage = Field(default_factory= TokenUsage)

Step = Annotated[
Union[UserMessageStep, AgentMessageStep, ToolCallStep, RetrievalStep, LLMCallStep],
Field(discriminator="step_type"),
]

class RunStatus(str,Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    PARTIAL = "partial"


class Trace(BaseModel):
    metadata: TraceMetaData 
    steps : list[Step]
    run_status: RunStatus = RunStatus.SUCCESS


if __name__ == "__main__":

    tk = TokenUsage(prompt_tokens=500, completion_tokens=300, total_tokens=800)
    instance4 = LLMCallStep(step_index = 0, timestamp_start=datetime.now(timezone.utc),provider="model_provider01",model = "model_name01",prompt="where is indian subcontinent located",token_usage= tk)
    # print(instance4)

    docA = RetrievedDocument(doc_id= "101", content="this is doc 1")
    docB = RetrievedDocument(doc_id= "102", content="this is doc 2")
    instance3 = RetrievalStep(step_index= 0, timestamp_start= datetime.now(timezone.utc),query="what are doc names",retrieved_documents=[docA,docB])

    instance2 = ToolCallStep(step_index= 0, timestamp_start= datetime.now(timezone.utc),tool_name = "excel",tool_args={"pr_number": 42})

    instance1= StepBase(step_index= 0 , timestamp_start= datetime.now(timezone.utc))

    instance = TraceMetaData(agent_id = "sample_agent_id",agent_role = "sample_role",framework= "sample_framework")

    trace = Trace(metadata= instance,steps= [instance4,instance3,instance2],run_status=RunStatus.PARTIAL)
    print(len(trace.steps))
    print(trace.metadata.agent_id)
    print(trace.run_status)

    # raw = trace.model_dump_json(indent=3)
    # print(raw)

    # restored = Trace.model_validate_json(raw)
    # print(len(restored.steps))
    # print(type(restored.steps[0]))
    # print(type(restored.steps[1]))
    # print(type(restored.steps[2]))

