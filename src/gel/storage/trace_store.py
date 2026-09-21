import os 
from dotenv import load_dotenv
import psycopg
from psycopg.types.json import Json
from pathlib import Path
from gel.schema.trace import Trace,TraceMetaData,RetrievalStep,ToolCallStep,RetrievedDocument, TokenUsage, LLMCallStep, StepBase,RunStatus,Step
from datetime import datetime, timezone
from pydantic import TypeAdapter


schema_path = Path(__file__).parent/"schema.sql"

load_dotenv()
conn_string = os.environ["DATABASE_URL"]

conn = psycopg.connect(conn_string)


with open(schema_path) as f :
    sql = f.read()

with conn.cursor() as cur:
    cur.execute(sql)

conn.commit()
with conn.cursor() as cur:
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name = 'traces';")
    result = cur.fetchone()
    print(result)
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name = 'steps';")
    result = cur.fetchone()
    print(result)

def save_trace_metadata(conn, trace: Trace):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO traces (trace_id, agent_id, agent_role, framework, framework_version,adapter_version, schema_version, created_at, redaction_applied, redaction_filter_version, run_status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (trace.metadata.trace_id, trace.metadata.agent_id, trace.metadata.agent_role, trace.metadata.framework, trace.metadata.framework_version, trace.metadata.adapter_version, trace.metadata.schema_version, trace.metadata.created_at, trace.metadata.redaction_applied,trace.metadata.redaction_filter_version,trace.run_status)
        )
    conn.commit()


def save_steps(conn, trace: Trace):
    with conn.cursor() as cur:
        for step in trace.steps:
            cur.execute(
                "INSERT INTO steps (step_id, trace_id, step_index, step_type, parent_step_id, timestamp_start, timestamp_end, status, retry_count, cache_hit, redacted, latency_ms, was_rate_limited, error_type, error_message, cache_key, payload) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    step.step_id,
                    trace.metadata.trace_id,
                    step.step_index,
                    step.step_type,
                    step.parent_step_id,
                    step.timestamp_start,
                    step.timestamp_end,
                    step.status,
                    step.retry_count,
                    step.cache_hit,
                    step.redacted,
                    step.latency_ms,
                    step.was_rate_limited,
                    step.error_type,
                    step.error_message,
                    step.cache_key,
                    Json(step.model_dump(mode="json")),
                )
            )
    conn.commit()

def load_trace_metadata(conn,trace_id: str):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT trace_id, agent_id, agent_role, framework, framework_version, adapter_version, schema_version, created_at, redaction_applied, redaction_filter_version, run_status FROM traces WHERE trace_id = %s",
            (trace_id,)
        )
        row = cur.fetchone()
        return TraceMetaData(
            trace_id= row[0],
            agent_id= row[1],
            agent_role= row[2],
            framework= row[3],
            framework_version=row[4],
            adapter_version = row[5],
            schema_version = row[6],
            created_at = row[7],
            redaction_applied= row[8],
            redaction_filter_version = row[9]
        )

def load_steps(conn, trace_id: str) -> list[Step]:
    step_adapter = TypeAdapter(Step)
    with conn.cursor() as cur:
        cur.execute("SELECT payload FROM steps WHERE trace_id = %s ORDER BY step_index", (trace_id,))
        rows = cur.fetchall()

    steps = []
    for row in rows:
        payload = row[0]
        step = step_adapter.validate_python(payload)
        steps.append(step)
    return steps

def load_trace(conn,trace_id:str ) -> Trace:
    metadata = load_trace_metadata(conn, trace_id)
    steps = load_steps(conn,trace_id)
    with conn.cursor() as cur:
        cur.execute("SELECT run_status FROM traces WHERE trace_id = %s",(trace_id,))
        row = cur.fetchone()
    run_status = row[0]
    return Trace(metadata= metadata, steps = steps,run_status= run_status)







if __name__ == "__main__":

    tk = TokenUsage(prompt_tokens=500, completion_tokens=300, total_tokens=800)
    instance4 = LLMCallStep(step_index = 0, timestamp_start=datetime.now(timezone.utc),provider="model_provider01",model = "model_name01",prompt="where is indian subcontinent located",token_usage= tk)
    # print(instance4)

    docA = RetrievedDocument(doc_id= "101", content="this is doc 1")
    docB = RetrievedDocument(doc_id= "102", content="this is doc 2")
    instance3 = RetrievalStep(step_index= 0, timestamp_start= datetime.now(timezone.utc),query="what are doc names",retrieved_documents=[docA,docB])

    instance2 = ToolCallStep(step_index= 0, timestamp_start= datetime.now(timezone.utc),tool_name = "excel",tool_args={"pr_number": 42})

    instance1= StepBase(step_index= 0 , timestamp_start= datetime.now(timezone.utc))

    instance = TraceMetaData(agent_id = "sample_agent_id",agent_role = "sample_role",framework= "sample_framework")

    trace = Trace(metadata= instance,steps= [instance4,instance3,instance2],run_status=RunStatus.PARTIAL)


    save_trace_metadata(conn, trace)
    save_steps(conn, trace)


    loaded = load_trace(conn, trace.metadata.trace_id)
    assert loaded.model_dump() == trace.model_dump(), "round-trip mismatch!"
    print("round trip verified: zero data loss")

conn.close()