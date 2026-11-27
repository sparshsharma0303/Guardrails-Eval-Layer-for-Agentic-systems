import json
from collections import defaultdict

from gel.schema.eval_signal import EvalMethod, Severity, Signal
from gel.schema.trace import ToolCallStep, Trace

EVALUATOR_VERSION = "1.0.0"


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


def loop_severity(max_count: int, max_repeats: int = 3) -> Severity:
    if max_count <= max_repeats + 1:
        return Severity.LOW
    if max_count <= 2 * max_repeats:
        return Severity.MEDIUM
    if max_count <= 3 * max_repeats:
        return Severity.HIGH
    return Severity.CRITICAL


def evaluate_loops(trace: Trace, max_repeats: int = 3) -> Signal | None:
    """Return a rule-based Signal if any tool is called with identical arguments more than max_repeats times."""
    findings = detect_repeated_tool_calls(trace, max_repeats=max_repeats)
    if not findings:
        return None

    max_count = max(count for _, count, _ in findings)
    all_span_ids = [step_id for _, _, step_ids in findings for step_id in step_ids]
    evidence = [
        f"{tool_name} called {count}x with identical args"
        for tool_name, count, _ in findings
    ]

    return Signal(
        # Convention: 0.0 = loop detected (bad), matching groundedness where 0.0 = ungrounded
        score=0.0,
        severity=loop_severity(max_count, max_repeats),
        eval_method=EvalMethod.RULE_BASED,
        judge_model=None,
        prompt_version=None,
        evaluator_version=EVALUATOR_VERSION,
        rubric_breakdown={
            "num_loops": float(len(findings)),
            "max_repeat_count": float(max_count),
        },
        # Deterministic rule check -> full confidence
        confidence=1.0,
        evidence=evidence,
        known_limitations=(
            "Only exact-match repeats; near-identical args or cycles like "
            "A->B->A->B are not detected."
        ),
        trace_id=trace.metadata.trace_id,
        trace_span_ids=all_span_ids,
    )


if __name__ == "__main__":
    from datetime import datetime, timezone
    from uuid import uuid4

    import psycopg
    from gel.schema.trace import AgentMessageStep, TraceMetaData
    from gel.storage.signal_store import load_signal, save_signal
    from gel.storage.trace_store import conn_string, save_steps, save_trace_metadata

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

    def _make_trace(steps: list, trace_id: str = "t-loop") -> Trace:
        return Trace(
            metadata=TraceMetaData(
                trace_id=trace_id,
                agent_id="agent-1",
                agent_role="tester",
                framework="custom",
            ),
            steps=steps,
        )

    # --- loop_severity boundary tests (max_repeats=3) ---
    assert loop_severity(4, 3) == Severity.LOW
    assert loop_severity(5, 3) == Severity.MEDIUM
    assert loop_severity(6, 3) == Severity.MEDIUM
    assert loop_severity(7, 3) == Severity.HIGH
    assert loop_severity(9, 3) == Severity.HIGH
    assert loop_severity(10, 3) == Severity.CRITICAL
    print("loop_severity boundary tests passed")

    # --- evaluate_loops in-memory tests ---
    # 1. Clean trace -> None
    clean_trace = _make_trace(
        [_tool_step(i, f"s-{i}", "search", {"q": "gel"}) for i in range(3)]
    )
    assert evaluate_loops(clean_trace) is None

    # 2. Custom max_repeats=2 with 3 identical calls -> LOW severity
    sig_custom_max = evaluate_loops(clean_trace, max_repeats=2)
    assert sig_custom_max is not None
    assert sig_custom_max.severity == Severity.LOW

    # 3. 4 identical calls -> LOW severity, 1 loop in breakdown
    low_trace = _make_trace(
        [_tool_step(i, f"s-{i}", "search", {"q": "gel"}) for i in range(4)]
    )
    sig_low = evaluate_loops(low_trace)
    assert sig_low is not None
    assert sig_low.severity == Severity.LOW
    assert sig_low.score == 0.0
    assert sig_low.confidence == 1.0
    assert sig_low.eval_method == EvalMethod.RULE_BASED
    assert sig_low.rubric_breakdown == {"num_loops": 1.0, "max_repeat_count": 4.0}
    assert sig_low.evidence == ["search called 4x with identical args"]
    assert sig_low.trace_span_ids == ["s-0", "s-1", "s-2", "s-3"]

    # 4. 7 identical calls with max_repeats=3 -> at least HIGH
    high_trace = _make_trace(
        [_tool_step(i, f"s-{i}", "search", {"q": "gel"}) for i in range(7)]
    )
    sig_high = evaluate_loops(high_trace, max_repeats=3)
    assert sig_high is not None
    assert sig_high.severity in (Severity.HIGH, Severity.CRITICAL)
    assert sig_high.severity == Severity.HIGH

    # 5. Two different looping groups -> both appear in evidence and trace_span_ids
    multi_trace = _make_trace(
        [_tool_step(i, f"a-{i}", "search", {"q": "gel"}) for i in range(4)]
        + [_tool_step(i + 4, f"b-{i}", "fetch", {"id": 99}) for i in range(5)]
    )
    sig_multi = evaluate_loops(multi_trace)
    assert sig_multi is not None
    assert sig_multi.rubric_breakdown == {"num_loops": 2.0, "max_repeat_count": 5.0}
    assert "search called 4x with identical args" in sig_multi.evidence
    assert "fetch called 5x with identical args" in sig_multi.evidence
    assert sig_multi.trace_span_ids == [
        "a-0", "a-1", "a-2", "a-3",
        "b-0", "b-1", "b-2", "b-3", "b-4",
    ]

    # Non-ToolCallStep ignored -> None
    msg_only_trace = _make_trace(
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
    assert evaluate_loops(msg_only_trace) is None
    print("evaluate_loops in-memory tests passed")

    # 6. Neon DB round-trip
    with psycopg.connect(conn_string) as db_conn:
        db_trace = _make_trace(
            [_tool_step(i, f"db-s-{uuid4()}", "search", {"q": "neon"}) for i in range(4)],
            trace_id=f"t-loop-db-{uuid4()}",
        )
        save_trace_metadata(db_conn, db_trace)
        save_steps(db_conn, db_trace)

        db_signal = evaluate_loops(db_trace)
        assert db_signal is not None
        save_signal(db_conn, db_signal)

        loaded_signal = load_signal(db_conn, db_signal.signal_id)
        assert loaded_signal == db_signal
        print("evaluate_loops Neon round-trip test passed")