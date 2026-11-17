import os
from datetime import datetime, timezone

import psycopg
from dotenv import load_dotenv

from gel.evaluators.rule_based import evaluate_trace
from gel.redaction.patterns import redact_trace
from gel.schema.eval_signal import Signal
from gel.schema.trace import (
    AgentMessageStep,
    LLMCallStep,
    RunStatus,
    TokenUsage,
    ToolCallStep,
    Trace,
    TraceMetaData,
)
from gel.storage.signal_store import load_signal, save_signal
from gel.storage.trace_store import load_steps, save_steps, save_trace_metadata


def evaluate_and_save(conn, trace: Trace) -> list[Signal]:
    signals = evaluate_trace(trace)
    for signal in signals:
        save_signal(conn, signal)
    return signals


if __name__ == "__main__":
    load_dotenv()
    conn = psycopg.connect(os.environ["DATABASE_URL"])

    try:
        now = datetime.now(timezone.utc)

        tool_step = ToolCallStep(
            step_index=0,
            timestamp_start=now,
            tool_name="search",
            tool_args={"query": "weather"},
        )
        agent_step = AgentMessageStep(
            step_index=1,
            timestamp_start=now,
            content="Here is your password: 1234",
        )
        llm_step = LLMCallStep(
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
        )

        trace = Trace(
            metadata=TraceMetaData(
                agent_id="agent-1",
                agent_role="assistant",
                framework="custom",
            ),
            run_status=RunStatus.PARTIAL,
            steps=[tool_step, agent_step, llm_step],
        )

        trace, _ = redact_trace(trace)
        save_trace_metadata(conn, trace)
        save_steps(conn, trace)

        signals = evaluate_and_save(conn, trace)

        for s in signals:
            loaded = load_signal(conn, s.signal_id)
            assert loaded == s, f"Loaded signal {s.signal_id} did not match saved signal"

        password_signals = [
            s
            for s in signals
            if s.rubric_breakdown.get("forbidden_pattern") == 0.0
        ]
        assert len(password_signals) == 1, "Expected exactly one failed forbidden_pattern signal"

        saved_steps = load_steps(conn, trace.metadata.trace_id)
        saved_agent_steps = [
            st for st in saved_steps if isinstance(st, AgentMessageStep)
        ]
        assert len(saved_agent_steps) == 1
        assert password_signals[0].trace_span_ids == [saved_agent_steps[0].step_id]
        assert password_signals[0].trace_span_ids == [agent_step.step_id]

        print("evaluate_and_save pipeline tests passed!")
    finally:
        conn.close()