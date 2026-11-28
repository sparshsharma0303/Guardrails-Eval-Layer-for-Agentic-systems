from typing import Any

from gel.schema.eval_signal import EvalMethod, Severity, Signal
from gel.schema.trace import ToolCallStep, Trace

from gel.security.constants import EVALUATOR_VERSION

_KNOWN_LIMITATIONS = " ".join([
    "Validates argument names and Python types only; values, ranges, and content (e.g. path traversal strings) are not inspected.",
    "All schema arguments are treated as required; optional parameters are not supported yet.",
    "Strict isinstance checks flag an int passed where a float is expected.",
    "Tools absent from schemas are skipped; unapproved tool names are handled by the permissions check.",
    "Detection accuracy depends directly on the completeness of the provided tool schemas.",
])


def validate_tool_args(tool_args: dict[str, Any], schema: dict[str, type]) -> list[str]:
    """Validate a tool's argument dictionary against a simple {arg_name: expected_type} schema.

    Returns a list of human-readable problem descriptions. An empty list means valid.
    """
    problems: list[str] = []

    # 1. Check schema keys for missing arguments and type mismatches
    for arg_name, expected_type in schema.items():
        if arg_name not in tool_args:
            problems.append(f"missing argument '{arg_name}'")
            continue

        value = tool_args[arg_name]

        # Reject bool when int is expected (since bool subclasses int in Python)
        is_bool_for_int = expected_type is int and isinstance(value, bool)
        if is_bool_for_int or not isinstance(value, expected_type):
            actual_type_name = type(value).__name__
            problems.append(
                f"argument '{arg_name}' expected {expected_type.__name__}, got {actual_type_name}"
            )

    # 2. Check tool_args for unexpected extra arguments
    for arg_name in tool_args:
        if arg_name not in schema:
            problems.append(f"unexpected argument '{arg_name}'")

    return problems


def detect_invalid_tool_args(
    trace: Trace,
    schemas: dict[str, dict[str, type]],
) -> list[tuple[str, str, list[str]]]:
    """Scan all ToolCallStep entries in a trace and validate their arguments against schemas.

    Returns a list of (tool_name, step_id, problems) tuples in trace order for any
    tool call with one or more argument validation problems.
    """
    findings: list[tuple[str, str, list[str]]] = []

    for step in trace.steps:
        if not isinstance(step, ToolCallStep):
            continue

        schema = schemas.get(step.tool_name)
        if schema is None:
            continue

        problems = validate_tool_args(step.tool_args, schema)
        if problems:
            findings.append((step.tool_name, step.step_id, problems))

    return findings


def arg_severity(num_unexpected: int) -> Severity:
    """Classify severity based on whether any unexpected arguments were injected."""
    if num_unexpected >= 1:
        return Severity.HIGH
    return Severity.MEDIUM


def evaluate_tool_args(
    trace: Trace,
    schemas: dict[str, dict[str, type]],
) -> Signal | None:
    """Evaluate all tool calls in a trace against expected schemas and emit a Signal if invalid."""
    findings = detect_invalid_tool_args(trace, schemas)
    if not findings:
        return None

    num_invalid_calls = len(findings)
    num_problems = sum(len(problems) for _, _, problems in findings)
    num_unexpected = sum(
        1
        for _, _, problems in findings
        for p in problems
        if p.startswith("unexpected argument")
    )

    evidence = [
        f"{tool_name} (step {step_id}): {'; '.join(problems)}"
        for tool_name, step_id, problems in findings
    ]
    trace_span_ids = [step_id for _, step_id, _ in findings]

    return Signal(
        trace_id=trace.metadata.trace_id,
        score=0.0,
        severity=arg_severity(num_unexpected),
        eval_method=EvalMethod.RULE_BASED,
        confidence=1.0,  # Deterministic schema and type check
        evaluator_version=EVALUATOR_VERSION,
        judge_model=None,
        prompt_version=None,
        rubric_breakdown={
            "num_invalid_calls": float(num_invalid_calls),
            "num_problems": float(num_problems),
            "num_unexpected_args": float(num_unexpected),
        },
        evidence=evidence,
        trace_span_ids=trace_span_ids,
        known_limitations=_KNOWN_LIMITATIONS,
    )