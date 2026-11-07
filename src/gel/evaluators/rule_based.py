import json
from gel.schema.eval_signal import Signal,Severity,EvalMethod

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



if __name__ == "__main__":
    from pathlib import Path
    from gel.datasets.eval_dataset import load_dataset
    ds = load_dataset(Path(__file__).parents[3] / "datasets" / "rule-based-checks__v1.0.0.json")
    checks = {
        "valid_json": check_valid_json,
        "required_fields": check_required_fields,
        "max_length": check_max_length,
        "forbidden_pattern": check_forbidden_pattern,
        "tool_args": check_tool_args,
    }
    all_ok = True
    for task, fn in checks.items():
        cases = [c for c in ds.cases if c.task_type == task]
        bad = [c.case_id for c in cases if fn(c.input) != c.expected_label]
        print(f"{task}: {len(cases) - len(bad)}/{len(cases)}", "FAILED " + str(bad) if bad else "")
        all_ok = all_ok and not bad
    assert all_ok, "some checks disagree with the labels"
    print("all rule-based checks match the labeled dataset")
    from gel.schema.eval_signal import Severity
    ok = run_check(check_valid_json, "valid_json", '{"a": 1}', "t-1", ["s-1"])
    bad = run_check(check_valid_json, "valid_json", "not json", "t-1", ["s-1"])
    assert ok.score == 1.0 and bad.score == 0.0
    assert ok.severity == Severity.INFORMATIONAL and bad.severity == Severity.MEDIUM
    assert ok.evidence == [] and bad.evidence == ["not json"]
    assert Signal.model_validate_json(bad.model_dump_json()) == bad
    print("run_check tests passed")