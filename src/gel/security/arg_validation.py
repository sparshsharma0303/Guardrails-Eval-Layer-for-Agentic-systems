from typing import Any


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