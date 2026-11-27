import json
from collections import defaultdict

from gel.schema.trace import ToolCallStep, Trace


def detect_repeated_tool_calls(
    trace: Trace,
    max_repeats: int = 3,
) -> list[tuple[str, int, list[str]]]:
    grouped_step_ids: dict[tuple[str, str], list[str]] = defaultdict(list)

    for step in trace.steps:
        if not isinstance(step, ToolCallStep):
            continue
        key = (
            step.tool_name,
            json.dumps(step.tool_args, sort_keys=True, default=str),
        )
        grouped_step_ids[key].append(step.step_id)

    findings: list[tuple[str, int, list[str]]] = []
    for (tool_name, _), step_ids in grouped_step_ids.items():
        if len(step_ids) > max_repeats:
            findings.append((tool_name, len(step_ids), step_ids))

    return findings



if __name__ == "__main__":
    from datetime import datetime, timezone

    from gel.schema.trace import AgentMessageStep, TraceMetaData

    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def _tool_step(idx: int, step_id: str, tool_name: str, tool_args: dict) -> ToolCallStep:
        return ToolCallStep(
            step_id=step_id,
            step_index=idx,
            timestamp_start=_now(),
            tool_name=tool_name,
            tool_args=tool_args,
        )

    def _make_trace(steps: list) -> Trace:
        return Trace(
            metadata=TraceMetaData(
                trace_id="t-loop",
                agent_id="agent-1",
                agent_role="tester",
                framework="custom",
            ),
            steps=steps,
        )

    # 1. 4 identical calls -> 1 finding, count 4
    t1 = _make_trace(
        [_tool_step(i, f"s-{i}", "search", {"q": "gel"}) for i in range(4)]
    )
    res1 = detect_repeated_tool_calls(t1)
    assert res1 == [("search", 4, ["s-0", "s-1", "s-2", "s-3"])], res1

    # 2. 3 identical calls -> []
    t2 = _make_trace(
        [_tool_step(i, f"s-{i}", "search", {"q": "gel"}) for i in range(3)]
    )
    assert detect_repeated_tool_calls(t2) == []

    # 3. Same tool, different args -> []
    t3 = _make_trace(
        [_tool_step(i, f"s-{i}", "search", {"q": f"gel-{i}"}) for i in range(5)]
    )
    assert detect_repeated_tool_calls(t3) == []

    # 4. Alternating tools (A, B, A, B...) -> []
    t4 = _make_trace(
        [
            _tool_step(i, f"s-{i}", "tool_a" if i % 2 == 0 else "tool_b", {"x": 1})
            for i in range(6)
        ]
    )
    assert detect_repeated_tool_calls(t4) == []

    # 5. Same args with different key order -> counted as the same call
    t5 = _make_trace(
        [
            _tool_step(0, "s-0", "fetch", {"a": 1, "b": 2}),
            _tool_step(1, "s-1", "fetch", {"b": 2, "a": 1}),
            _tool_step(2, "s-2", "fetch", {"a": 1, "b": 2}),
            _tool_step(3, "s-3", "fetch", {"b": 2, "a": 1}),
        ]
    )
    res5 = detect_repeated_tool_calls(t5)
    assert res5 == [("fetch", 4, ["s-0", "s-1", "s-2", "s-3"])], res5

    # 6. Empty trace -> []
    t6 = _make_trace([])
    assert detect_repeated_tool_calls(t6) == []

    # Non-ToolCallStep ignored
    t7 = _make_trace(
        [
            AgentMessageStep(
                step_id=f"m-{i}",
                step_index=i,
                timestamp_start=_now(),
                content="hello",
            )
            for i in range(5)
        ]
    )
    assert detect_repeated_tool_calls(t7) == []

    print("loop_detection tests passed")