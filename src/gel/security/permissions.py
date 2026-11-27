from gel.schema.trace import ToolCallStep, Trace


def detect_unauthorized_tool_calls(
    trace: Trace,
    allowed_tools: set[str],
) -> list[tuple[str, str]]:
    """Return (tool_name, step_id) for every ToolCallStep not in allowed_tools."""
    violations: list[tuple[str, str]] = []

    for step in trace.steps:
        if not isinstance(step, ToolCallStep):
            continue
        if step.tool_name not in allowed_tools:
            violations.append((step.tool_name, step.step_id))

    return violations


if __name__ == "__main__":
    from datetime import datetime, timezone

    from gel.schema.trace import AgentMessageStep, TraceMetaData

    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _tool_step(idx: int, step_id: str, tool_name: str) -> ToolCallStep:
        return ToolCallStep(
            step_id=step_id,
            step_index=idx,
            timestamp_start=_now(),
            tool_name=tool_name,
            tool_args={},
        )

    def _make_trace(steps: list) -> Trace:
        return Trace(
            metadata=TraceMetaData(
                trace_id="t-perm",
                agent_id="agent-1",
                agent_role="tester",
                framework="custom",
            ),
            steps=steps,
        )

    # 1. All calls inside the allow-list -> []
    t_ok = _make_trace(
        [
            _tool_step(0, "s-0", "search"),
            _tool_step(1, "s-1", "read_doc"),
        ]
    )
    assert detect_unauthorized_tool_calls(t_ok, {"search", "read_doc"}) == []

    # 2. One call outside it -> 1 finding with the correct step_id
    t_one_bad = _make_trace(
        [
            _tool_step(0, "s-0", "search"),
            _tool_step(1, "s-1", "delete_db"),
        ]
    )
    assert detect_unauthorized_tool_calls(t_one_bad, {"search"}) == [
        ("delete_db", "s-1")
    ]

    # 3. The same unauthorized tool called twice -> 2 findings
    t_two_bad = _make_trace(
        [
            _tool_step(0, "s-0", "exec_shell"),
            _tool_step(1, "s-1", "search"),
            _tool_step(2, "s-2", "exec_shell"),
        ]
    )
    assert detect_unauthorized_tool_calls(t_two_bad, {"search"}) == [
        ("exec_shell", "s-0"),
        ("exec_shell", "s-2"),
    ]

    # 4. Empty allow-list -> every tool call flagged
    assert detect_unauthorized_tool_calls(t_ok, set()) == [
        ("search", "s-0"),
        ("read_doc", "s-1"),
    ]

    # 5. Empty trace -> []
    assert detect_unauthorized_tool_calls(_make_trace([]), {"search"}) == []

    # 6. Non-tool steps are ignored
    t_non_tool = _make_trace(
        [
            AgentMessageStep(
                step_id="m-0",
                step_index=0,
                timestamp_start=_now(),
                content="hello",
            )
        ]
    )
    assert detect_unauthorized_tool_calls(t_non_tool, set()) == []

    print("permissions tests passed")