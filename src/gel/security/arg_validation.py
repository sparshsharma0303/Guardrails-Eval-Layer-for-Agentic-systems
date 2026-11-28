from typing import Any

from gel.schema.trace import ToolCallStep, Trace


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