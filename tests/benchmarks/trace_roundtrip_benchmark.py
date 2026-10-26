import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from tests.fixtures.minimal_langgraph_agents import app
from gel.adapters.langgraph_adapter import langgraph_stream_to_trace
from gel.schema.trace import Trace

results = []
test_messages = [f"test message {i}" for i in range(10)]

for i, msg in enumerate(test_messages):
    try:
        stream = list(app.stream({"user_message": msg}, stream_mode="updates"))
        trace = langgraph_stream_to_trace(agent_id="benchmark_agent", agent_role="benchmark", stream_output=stream)
        raw = trace.model_dump_json()
        restored = Trace.model_validate_json(raw)
        if (trace.model_dump() == restored.model_dump()):
            results.append((i, True))
        else:
            results.append((i,False,"mismatch"))
    except Exception as e:
        results.append((i, False,str(e)))

passed = [r for r in results if r[1]==True]
failed = [r for r in results if r[1]==False]

print(f"total number of passed are {len(passed)}")
if len(failed)!= 0 :
    for f in failed:
        print(f"number {f[0]} failed because of {f[2]}")
assert len(failed) == 0, f"{len(failed)}/10 runs failed the round-trip benchmark"
