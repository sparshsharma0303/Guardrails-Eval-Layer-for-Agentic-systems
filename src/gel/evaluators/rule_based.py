import json
from gel.schema.eval_signal import Signal,Severity,EvalMethod
from gel.schema.trace import ToolCallStep,AgentMessageStep,LLMCallStep,Trace,TraceMetaData,RunStatus,TokenUsage
import json
from typing import Any
from datetime import datetime, timezone

def check_valid_json(text):
    try:
        json.loads(text)
        return True
    except ValueError:
        return False

def check_required_fields(text):
    try:
        data = json.loads(text)
        if not isinstance(data,dict):
            return False
        return "answer" in data and "confidence" in data
    except (ValueError,TypeError):
        return False

def check_max_length(text, limit=50):
    return len(text) <= limit

def check_forbidden_pattern(text):
    return "password" not in text.lower()

def check_tool_args(text):
    try:
        data = json.loads(text)
        
        if not isinstance(data, dict):
            return False
            
        if data.get("tool_name") != "search":
            return False
            
        args = data.get("args")
        if not isinstance(args, dict):
            return False
            
        query = args.get("query")
        if not isinstance(query, str) or not query.strip():
            return False
            
        return True
        
    except (ValueError, TypeError):
        return False

EVALUATOR_VERSION = "1.0.0"

def run_check(check_fn, check_name, text, trace_id, trace_span_ids) -> Signal:
    """
    Executes a rule-based check function on the given text and wraps the result 
    into a standardized Signal object.
    """
    try:
        passed = bool(check_fn(text))
    except Exception:
        passed = False

    if passed:
        score = 1.0
        severity = Severity.INFORMATIONAL
        evidence = []
    else:
        score = 0.0
        severity = Severity.MEDIUM
        evidence = [text[:200]]

    return Signal(
        score=score,
        severity=severity,
        eval_method=EvalMethod.RULE_BASED,
        evaluator_version=EVALUATOR_VERSION,
        rubric_breakdown={check_name: score},
        evidence=evidence,
        trace_id=trace_id,
        trace_span_ids=trace_span_ids,
        confidence=1.0,
        known_limitations="Deterministic rule; checks syntax only, not meaning.",
        judge_model=None,
        prompt_version=None
    )


def evaluate_trace(trace: Trace) -> list[Signal]:
    signals: list[Signal] = []
    trace_id = trace.metadata.trace_id

    for step in trace.steps:
        span_ids = [step.step_id]

        if isinstance(step, ToolCallStep):
            signal = run_check(
                check_valid_json,
                "tool_args_valid_json",
                json.dumps(step.tool_args),
                trace_id,
                span_ids,
            )
            signals.append(signal)

        elif isinstance(step, AgentMessageStep):
            signal = run_check(
                check_forbidden_pattern,
                "forbidden_pattern",
                step.content,
                trace_id,
                span_ids,
            )
            signals.append(signal)

        elif isinstance(step, LLMCallStep) and step.completion is not None:
            signal = run_check(
                check_forbidden_pattern,
                "forbidden_pattern",
                step.completion,
                trace_id,
                span_ids,
            )
            signals.append(signal)

    return signals

if __name__ == "__main__":
    from pathlib import Path
    from gel.datasets.eval_dataset import load_dataset
    # ds = load_dataset(Path(__file__).parents[3] / "datasets" / "rule-based-checks__v1.0.0.json")
    # checks = {
    #     "valid_json": check_valid_json,
    #     "required_fields": check_required_fields,
    #     "max_length": check_max_length,
    #     "forbidden_pattern": check_forbidden_pattern,
    #     "tool_args": check_tool_args,
    # }
    # all_ok = True
    # for task, fn in checks.items():
    #     cases = [c for c in ds.cases if c.task_type == task]
    #     bad = [c.case_id for c in cases if fn(c.input) != c.expected_label]
    #     print(f"{task}: {len(cases) - len(bad)}/{len(cases)}", "FAILED " + str(bad) if bad else "")
    #     all_ok = all_ok and not bad
    # assert all_ok, "some checks disagree with the labels"
    # print("all rule-based checks match the labeled dataset")
    # from gel.schema.eval_signal import Severity
    # ok = run_check(check_valid_json, "valid_json", '{"a": 1}', "t-1", ["s-1"])
    # bad = run_check(check_valid_json, "valid_json", "not json", "t-1", ["s-1"])
    # assert ok.score == 1.0 and bad.score == 0.0
    # assert ok.severity == Severity.INFORMATIONAL and bad.severity == Severity.MEDIUM
    # assert ok.evidence == [] and bad.evidence == ["not json"]
    # assert Signal.model_validate_json(bad.model_dump_json()) == bad
    # print("run_check tests passed")

    now = datetime.now(timezone.utc)

    sample_trace = Trace(
        metadata=TraceMetaData(
            trace_id="trace-1",
            agent_id="agent-1",
            agent_role="assistant",
            framework="custom",
        ),
        run_status=RunStatus.PARTIAL,
        steps=[
            ToolCallStep(
                step_id="step-1",
                step_index=0,
                timestamp_start=now,
                tool_name="search",
                tool_args={"query": "weather"},
            ),
            AgentMessageStep(
                step_id="step-2",
                step_index=1,
                timestamp_start=now,
                content="Here is your password: 1234",
            ),
            LLMCallStep(
                step_id="step-3",
                step_index=2,
                timestamp_start=now,
                provider="openai",
                model="gpt-4o",
                prompt="Tell me a secret",
                completion=None,
                token_usage=TokenUsage(
                    prompt_tokens=10,
                    completion_tokens=0,
                    total_tokens=10,
                ),
            ),
        ],
    )

    signals = evaluate_trace(sample_trace)

    assert len(signals) == 2
    assert signals[0].trace_span_ids == ["step-1"]
    assert signals[1].trace_span_ids == ["step-2"]
    assert signals[1].score == 0.0
    print("evaluate_trace tests passed!")