import re
from gel.schema.trace import UserMessageStep,AgentMessageStep,ToolCallStep,RetrievalStep,LLMCallStep,RetrievedDocument,Trace,TraceMetaData,StepBase, TokenUsage, RunStatus
from datetime import datetime, timezone
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
AWS_ACCESS_KEY = re.compile(r"AKIA[A-Z0-9]{16}")
GITHUB_TOKEN = re.compile(r"\bghp_[A-Za-z0-9]{36}\b")
BEARER_TOKEN = re.compile(r"\bBearer\s+[A-Za-z0-9._%+-]+\b")

PATTERNS = {
    "EMAIL": EMAIL,
    "AWS_ACCESS_KEY": AWS_ACCESS_KEY,
    "GITHUB_TOKEN": GITHUB_TOKEN,
    "BEARER_TOKEN": BEARER_TOKEN,
}

def redact_text(text: str, prefix: str = "REDACTED") -> tuple[str,list[str]]:
    redacted_text = text
    fired = []
    for label,pattern in PATTERNS.items():
        if re.findall(pattern= PATTERNS[label],string = text ):
            fired.append(label)
            redacted_text = pattern.sub(f"[{prefix}:{label}]",redacted_text)

    return redacted_text,fired

def redact_value(value)-> tuple[str,list[str]]:
    fired = []
    if isinstance(value,str):
        redacted, fired = redact_text(value)
        return redacted, fired
    elif isinstance(value,dict):
        new_dict = {}
        for key,val in value.items():
            redacted_val, fired_val= redact_value(val)
            new_dict[key] = redacted_val
            fired.extend(fired_val)

        return new_dict, fired
    elif isinstance(value,list):
        new_list = []
        for item in value:
            redacted_val,fired_val = redact_value(item)
            new_list.append(redacted_val)
            fired.extend(fired_val)
        return new_list,fired
    else:
        return value, fired

def redact_step(step):
    fired = []
    redacted_meta, fired_meta = redact_value(step.framework_metadata)
    step.framework_metadata = redacted_meta
    fired.extend(fired_meta)

    if isinstance(step,(UserMessageStep,AgentMessageStep)):
        redacted_content, fired_content = redact_text(step.content)
        step.content = redacted_content
        fired.extend(fired_content)
        if fired:
            step.redacted = True
        return step, fired

    if isinstance(step,(ToolCallStep)):  
        redacted_args, fired_args = redact_value(step.tool_args)
        redacted_result,fired_result = redact_value(step.tool_result)
        step.tool_args = redacted_args
        step.tool_result = redacted_result
        fired.extend(fired_args)
        fired.extend(fired_result)
        if fired:
            step.redacted = True
        return step,fired

    if isinstance(step,(RetrievalStep)):
        redacted_query, fired_query = redact_text(step.query)
        step.query = redacted_query
        fired.extend(fired_query)
        for doc in step.retrieved_documents:
            redacted_content, fired_content = redact_text(doc.content)
            doc.content = redacted_content
            if doc.source:
                redacted_source, fired_source = redact_text(doc.source)
                doc.source = redacted_source
                fired.extend(fired_source)
            fired.extend(fired_content)
        if fired:
            step.redacted = True
        return step, fired

    if isinstance(step,(LLMCallStep)):
        redacted_prompt, fired_prompt = redact_text(step.prompt)
        step.prompt = redacted_prompt
        fired.extend(fired_prompt)
        if step.completion :
            redacted_completion, fired_completion = redact_text(step.completion)
            step.completion = redacted_completion
            fired.extend(fired_completion)
        if fired:
            step.redacted = True
        return step, fired

def redact_trace(trace:Trace) -> Trace:
    all_fired = []
    for step in trace.steps:
        redacted_step, redact_fired = redact_step(step)
        all_fired.extend(redact_fired)
    if all_fired:
        trace.metadata.redaction_applied = True
        trace.metadata.redaction_filter_version = "1.0.0"
    return trace, all_fired


if __name__ == "__main__":

    tk = TokenUsage(prompt_tokens=500, completion_tokens=300, total_tokens=800)
    instance4 = LLMCallStep(
            step_index=0,
            timestamp_start=datetime.now(timezone.utc),
            provider="model_provider01",
            model="model_name01",
            prompt="email the results to sparsh@example.com",
            completion="Sure, sending to sparsh@example.com now.",
            token_usage=tk,
        )
    # print(instance4)

    docA = RetrievedDocument(doc_id= "101", content="send this mail to sparshsharma0303@gmail.com ")
    docB = RetrievedDocument(doc_id= "102", content="the random api key is the Bearer eyJhbGciOiJIUzI1NiJ9.abcXYZ123")
    instance3 = RetrievalStep(step_index= 0, timestamp_start= datetime.now(timezone.utc),query="what are doc names",retrieved_documents=[docA,docB])

    instance2 = ToolCallStep(step_index= 0, timestamp_start= datetime.now(timezone.utc),tool_name = "excel",tool_args={"AWS_APIKEY": "AKIAIOSFODNN7EXAMPLE"})

    instance1= StepBase(step_index= 0 , timestamp_start= datetime.now(timezone.utc))

    instance = TraceMetaData(agent_id = "sample_agent_id",agent_role = "sample_role",framework= "sample_framework")

    trace = Trace(metadata= instance,steps= [instance4,instance3,instance2],run_status=RunStatus.PARTIAL)


    redacted_trace, fired = redact_trace(trace=trace)
    print(f'the fired values of the trace are : \n {fired}')

    for step in redacted_trace.steps:
        print(f'redacted_step: \n {step}')
        print("-"*50)

    print(f'redaction applied: {redacted_trace.metadata.redaction_applied}')
    print(f'redaction applied: {redacted_trace.metadata.redaction_filter_version}')