from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import psycopg

from gel.schema.eval_signal import EvalMethod, Severity
from gel.schema.trace import AgentMessageStep, ToolCallStep, Trace, TraceMetaData
from gel.security.arg_validation import (
    arg_severity,
    detect_invalid_tool_args,
    evaluate_tool_args,
    validate_tool_args,
)
from gel.storage.signal_store import load_signal, save_signal
from gel.storage.trace_store import conn_string, save_trace_metadata


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _tool_step(
    step_id: str,
    tool_name: str,
    tool_args: dict[str, Any] | None = None,
    idx: int = 0,
) -> ToolCallStep:
    return ToolCallStep(
        step_id=step_id,
        step_index=idx,
        timestamp_start=_now(),
        tool_name=tool_name,
        tool_args=tool_args if tool_args is not None else {},
    )


def _make_trace(steps: list[Any], trace_id: str = "trace-test-1") -> Trace:
    return Trace(
        metadata=TraceMetaData(
            trace_id=trace_id,
            agent_id="agent-test",
            agent_role="reviewer",
            framework="langgraph",
            created_at=_now(),
        ),
        steps=steps,
    )


# --- Step A: validate_tool_args ---


def test_valid_args():
    schema = {"query": str, "limit": int}
    args = {"query": "security logs", "limit": 10}
    assert validate_tool_args(args, schema) == []


def test_missing_arg():
    schema = {"query": str, "limit": int}
    args = {"query": "security logs"}
    assert validate_tool_args(args, schema) == ["missing argument 'limit'"]


def test_extra_arg():
    schema = {"query": str, "limit": int}
    args = {"query": "security logs", "limit": 10, "admin": True}
    assert validate_tool_args(args, schema) == ["unexpected argument 'admin'"]


def test_wrong_type():
    schema = {"query": str, "limit": int}
    args = {"query": "security logs", "limit": "10"}
    assert validate_tool_args(args, schema) == [
        "argument 'limit' expected int, got str"
    ]


def test_multiple_problems_reported_in_predictable_order():
    schema = {"query": str, "limit": int, "offset": int}
    args = {"query": 123, "offset": 0, "debug": True}

    assert validate_tool_args(args, schema) == [
        "argument 'query' expected str, got int",
        "missing argument 'limit'",
        "unexpected argument 'debug'",
    ]


def test_empty_args_and_empty_schema():
    assert validate_tool_args({}, {}) == []


def test_bool_is_rejected_when_int_expected():
    schema = {"limit": int}
    args = {"limit": True}
    assert validate_tool_args(args, schema) == [
        "argument 'limit' expected int, got bool"
    ]


def test_bool_is_accepted_when_bool_expected():
    schema = {"dry_run": bool}
    args = {"dry_run": True}
    assert validate_tool_args(args, schema) == []


# --- Step B: detect_invalid_tool_args ---


def test_trace_all_calls_valid():
    schemas = {
        "search": {"query": str, "limit": int},
        "ping": {},
    }
    trace = _make_trace(
        [
            _tool_step("s1", "search", {"query": "errors", "limit": 5}, idx=0),
            _tool_step("s2", "ping", {}, idx=1),
        ]
    )
    assert detect_invalid_tool_args(trace, schemas) == []


def test_trace_one_bad_call():
    schemas = {"search": {"query": str, "limit": int}}
    trace = _make_trace(
        [
            _tool_step("s1", "search", {"query": "errors", "limit": "five"}),
        ]
    )
    assert detect_invalid_tool_args(trace, schemas) == [
        ("search", "s1", ["argument 'limit' expected int, got str"])
    ]


def test_trace_unknown_tool_ignored():
    schemas = {"search": {"query": str}}
    trace = _make_trace(
        [
            _tool_step("s1", "unregistered_tool", {"anything": 123}),
        ]
    )
    assert detect_invalid_tool_args(trace, schemas) == []


def test_trace_call_with_several_problems():
    schemas = {"search": {"query": str, "limit": int}}
    trace = _make_trace(
        [
            _tool_step("s1", "search", {"query": 42, "sudo": True}),
        ]
    )
    assert detect_invalid_tool_args(trace, schemas) == [
        (
            "search",
            "s1",
            [
                "argument 'query' expected str, got int",
                "missing argument 'limit'",
                "unexpected argument 'sudo'",
            ],
        )
    ]


def test_trace_two_bad_calls_preserve_trace_order():
    schemas = {
        "search": {"query": str},
        "delete": {"id": int},
    }
    trace = _make_trace(
        [
            _tool_step("s1", "search", {}, idx=0),
            _tool_step("s2", "search", {"query": "ok"}, idx=1),
            _tool_step("s3", "delete", {"id": "not-an-int"}, idx=2),
        ]
    )
    assert detect_invalid_tool_args(trace, schemas) == [
        ("search", "s1", ["missing argument 'query'"]),
        ("delete", "s3", ["argument 'id' expected int, got str"]),
    ]


def test_trace_empty():
    schemas = {"search": {"query": str}}
    trace = _make_trace([])
    assert detect_invalid_tool_args(trace, schemas) == []


def test_trace_non_tool_steps_ignored():
    schemas = {"search": {"query": str}}
    trace = _make_trace(
        [
            AgentMessageStep(
                step_id="m1",
                step_index=0,
                timestamp_start=_now(),
                content="Checking logs now.",
            ),
            _tool_step("s1", "search", {"query": "ok"}, idx=1),
        ]
    )
    assert detect_invalid_tool_args(trace, schemas) == []


def test_trace_empty_schema_flags_any_argument():
    schemas = {"healthcheck": {}}
    trace = _make_trace(
        [
            _tool_step("s1", "healthcheck", {"force": True}),
        ]
    )
    assert detect_invalid_tool_args(trace, schemas) == [
        ("healthcheck", "s1", ["unexpected argument 'force'"])
    ]


# --- Piece 6: arg_severity & evaluate_tool_args ---


def test_arg_severity_boundaries():
    assert arg_severity(0) == Severity.MEDIUM
    assert arg_severity(1) == Severity.HIGH
    assert arg_severity(4) == Severity.HIGH


def test_evaluate_clean_trace_returns_none():
    schemas = {"search": {"query": str, "limit": int}}
    trace = _make_trace(
        [
            _tool_step("s1", "search", {"query": "alerts", "limit": 10}),
        ]
    )
    assert evaluate_tool_args(trace, schemas) is None


def test_evaluate_wrong_type_only_is_medium():
    schemas = {"search": {"query": str, "limit": int}}
    trace = _make_trace(
        [
            _tool_step("s1", "search", {"query": "alerts", "limit": "ten"}),
        ]
    )
    signal = evaluate_tool_args(trace, schemas)
    assert signal is not None
    assert signal.score == 0.0
    assert signal.severity == Severity.MEDIUM
    assert signal.eval_method == EvalMethod.RULE_BASED
    assert signal.confidence == 1.0
    assert signal.judge_model is None
    assert signal.prompt_version is None
    assert signal.rubric_breakdown == {
        "num_invalid_calls": 1.0,
        "num_problems": 1.0,
        "num_unexpected_args": 0.0,
    }
    assert signal.evidence == [
        "search (step s1): argument 'limit' expected int, got str"
    ]
    assert signal.trace_span_ids == ["s1"]
    assert "path traversal" in signal.known_limitations


def test_evaluate_unexpected_argument_is_high():
    schemas = {"search": {"query": str}}
    trace = _make_trace(
        [
            _tool_step("s1", "search", {"query": "alerts", "admin": True}),
        ]
    )
    signal = evaluate_tool_args(trace, schemas)
    assert signal is not None
    assert signal.severity == Severity.HIGH
    assert signal.rubric_breakdown["num_unexpected_args"] == 1.0


def test_evaluate_two_bad_calls_breakdown_and_order():
    schemas = {
        "search": {"query": str, "limit": int},
        "delete": {"id": int},
    }
    trace = _make_trace(
        [
            _tool_step("s1", "search", {"query": "logs", "limit": "5", "sudo": True}, idx=0),
            _tool_step("s2", "search", {"query": "ok", "limit": 1}, idx=1),
            _tool_step("s3", "delete", {}, idx=2),
        ]
    )
    signal = evaluate_tool_args(trace, schemas)
    assert signal is not None
    assert signal.severity == Severity.HIGH
    assert signal.rubric_breakdown == {
        "num_invalid_calls": 2.0,
        "num_problems": 3.0,
        "num_unexpected_args": 1.0,
    }
    assert signal.evidence == [
        "search (step s1): argument 'limit' expected int, got str; unexpected argument 'sudo'",
        "delete (step s3): missing argument 'id'",
    ]
    assert signal.trace_span_ids == ["s1", "s3"]


def test_evaluate_tool_args_neon_round_trip():
    trace_id = f"t-args-db-{uuid4()}"
    schemas = {"search": {"query": str, "limit": int}}
    trace = _make_trace(
        [
            _tool_step("s1", "search", {"query": "logs", "limit": "bad", "sudo": True}),
        ],
        trace_id=trace_id,
    )
    signal = evaluate_tool_args(trace, schemas)
    assert signal is not None

    with psycopg.connect(conn_string) as conn:
        save_trace_metadata(conn, trace)
        save_signal(conn, signal)
        loaded = load_signal(conn, signal.signal_id)

    assert loaded == signal