import os
from dotenv import load_dotenv
import psycopg
from psycopg.errors import ForeignKeyViolation
from psycopg.types.json import Json
from pathlib import Path
from gel.schema.eval_signal import Signal,EvalMethod,Severity
from gel.schema.trace import Trace,TraceMetaData,RunStatus
from gel.storage.trace_store import save_steps, save_trace_metadata
from gel.redaction.patterns import redact_trace


def save_signal(conn, signal):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO signals (signal_id,trace_id, timestamp, evaluator_version, score, severity,eval_method, payload) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (signal.signal_id,
            signal.trace_id,
            signal.timestamp,
            signal.evaluator_version,
            signal.score,
            signal.severity.value,
            signal.eval_method.value,
            Json(signal.model_dump(mode="json")),)
        )
    conn.commit()

def load_signal(conn, signal_id):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT payload FROM signals WHERE signal_id = %s",(signal_id,)
        )
        row = cur.fetchone()
    if row is not None :
        signal = Signal.model_validate(row[0])
        return signal
    else:
        return None


if __name__ == "__main__":
    schema_path = Path(__file__).parent/"schema.sql"
    load_dotenv()
    conn_string = os.environ["DATABASE_URL"]
    conn = psycopg.connect(conn_string)

    trace_instance = TraceMetaData(agent_id = "sample_agent_id",agent_role = "sample_role",framework= "sample_framework")
    trace = Trace(metadata= trace_instance,steps= [],run_status=RunStatus.PARTIAL)
    trace, fired = redact_trace(trace=trace)
    save_trace_metadata(conn, trace=trace)
    save_steps(conn, trace)
    
    evidence=["span one"]
    trace_span_ids=["step-1"]
    known_limitations = "none known"
    signal_instance = Signal(trace_id=trace_instance.trace_id,evaluator_version="1.0.0",score = 0.9, confidence= 0.7, severity=Severity.LOW,eval_method = EvalMethod.HUMAN,rubric_breakdown={"relevance": 0.8},evidence= evidence,known_limitations=known_limitations,trace_span_ids=trace_span_ids)
    save_signal(conn=conn, signal=signal_instance)
    try:
        signal_instance2 = Signal(trace_id="nonexistent-trace-id",evaluator_version="1.0.0",score = 0.9, confidence= 0.7, severity=Severity.LOW,eval_method = EvalMethod.HUMAN,rubric_breakdown={"relevance": 0.8},evidence= evidence,known_limitations=known_limitations,trace_span_ids=trace_span_ids)
        save_signal(conn = conn, signal=signal_instance2)
    except ForeignKeyViolation:
        print("succefully failed insertion of signal_instace in DB with dummy trace_id")
        conn.rollback()
    except Exception as e :
        print("unexpected Exception", e)
    loaded = load_signal(conn, signal_id= signal_instance.signal_id)
    assert loaded.model_dump() == signal_instance.model_dump(), "some data lost"
    assert load_signal(conn, "does-not-exit") is None, "test for dummy  signal id failed"   
    print('single round trip passed')
    conn.close()