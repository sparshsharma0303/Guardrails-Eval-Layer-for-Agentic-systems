import os
from datetime import datetime, timezone

import psycopg
from dotenv import load_dotenv

from gel.groundedness.evaluate import evaluate_trace_groundedness
from gel.redaction.patterns import redact_trace
from gel.schema.eval_signal import Severity
from gel.schema.trace import (
    AgentMessageStep, RetrievalStep, RetrievedDocument, RunStatus, Trace, TraceMetaData, UserMessageStep,
)
from gel.storage.signal_store import load_signal, save_signal
from gel.storage.trace_store import load_steps, save_steps, save_trace_metadata


def build_trace(answer: str, with_retrieval: bool = True) -> Trace:
    now = datetime.now(timezone.utc)
    steps = [UserMessageStep(step_index=0, timestamp_start=now, content="What is the capital of France?")]
    if with_retrieval:
        steps.append(RetrievalStep(
            step_index=1, timestamp_start=now, query="capital of France",
            retrieved_documents=[RetrievedDocument(
                doc_id="d1", content="Paris is the capital of France. It sits on the Seine river.")],
        ))
    steps.append(AgentMessageStep(step_index=len(steps), timestamp_start=now,
                                  content=answer, is_final_answer=True))
    return Trace(metadata=TraceMetaData(agent_id="agent-1", agent_role="assistant", framework="custom"),
                 run_status=RunStatus.PARTIAL, steps=steps)


if __name__ == "__main__":
    load_dotenv()
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    try:
        trace, _ = redact_trace(build_trace("Paris is the capital of Germany."))
        save_trace_metadata(conn, trace)
        save_steps(conn, trace)

        sig = evaluate_trace_groundedness(trace)
        assert sig is not None and sig.severity == Severity.HIGH and sig.evidence

        # every span id on the signal must exist in the stored trace
        stored_ids = {s.step_id for s in load_steps(conn, trace.metadata.trace_id)}
        assert sig.trace_span_ids and set(sig.trace_span_ids) <= stored_ids
        assert trace.steps[1].step_id in sig.trace_span_ids and trace.steps[2].step_id in sig.trace_span_ids

        save_signal(conn, sig)
        assert load_signal(conn, sig.signal_id) == sig

        # no retrieval steps: groundedness does not apply, so no signal
        assert evaluate_trace_groundedness(build_trace("Anything.", with_retrieval=False)) is None

        print("Integration Check 2 passed")
        print(sig.severity, sig.score, sig.trace_span_ids)
        print(sig.evidence)
    finally:
        conn.close()