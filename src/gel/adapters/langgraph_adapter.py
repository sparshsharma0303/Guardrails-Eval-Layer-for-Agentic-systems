from gel.schema.trace import Trace, TraceMetaData, AgentMessageStep,ToolCallStep, RetrievedDocument,RetrievalStep,LLMCallStep
from datetime import datetime,timezone
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures.minimal_langgraph_agents import app

def langgraph_stream_to_trace(agent_id: str, agent_role: str,stream_output : list[dict]) -> Trace:
    metadata = TraceMetaData(agent_id=agent_id, agent_role=agent_role, framework="langgraph")
    steps = []

    for index, item in enumerate(stream_output):
        node_name , changes = list(item.items())[0]

        if "tool_name" in changes : 
            steps.append(ToolCallStep(step_index=index,timestamp_start=datetime.now(timezone.utc),tool_name=changes["tool_name"],tool_args=changes["tool_args"],tool_result= changes["tool_result"]))
        elif "query" in changes:
            #  retrivalstep
            docs = []
            for d in changes["retrieved_docs"]:
                docs.append(RetrievedDocument(doc_id=d["doc_id"],content = d["content"]))
            steps.append(RetrievalStep(step_index = index ,timestamp_start = datetime.now(timezone.utc), query=changes["query"], retrieved_documents=docs))
        elif "prompt" in changes:
            steps.append(LLMCallStep(step_index=index,timestamp_start=datetime.now(timezone.utc),provider="unknown",model="unknown",prompt=changes["prompt"],completion=changes["completion"]))
        else:
            is_final = (node_name == "respond")
            steps.append(AgentMessageStep(step_index=index, timestamp_start=datetime.now(timezone.utc), content= list(changes.values())[0], is_final_answer=is_final))
    trace = Trace(metadata=metadata, steps= steps)
    return trace


if __name__ == "__main__":

    # fake_stream = [
    #     {'my_node': {'agent_response': 'this is a fixed text response'}},
    #     {'my_node2': {'summary': 'response was generated'}},
    # ]

    real_stream = list(app.stream({"user_message": "hello agent"},stream_mode="updates"))

    instance = langgraph_stream_to_trace(agent_id="001", agent_role="message", stream_output=real_stream)
    print(instance.metadata.agent_id)
    print(len(instance.steps))
    # print(instance.steps[0].content)
    # print(instance.steps[0].tool_result)
    print(type(instance.steps[0]))
    print(type(instance.steps[1]))
    print(type(instance.steps[2]))
    print(type(instance.steps[3]))
    print(type(instance.steps[4]))
    print(instance.steps[1].prompt)
    print(instance.steps[1].completion)
    print(instance.steps[3].content, instance.steps[3].is_final_answer)
    print(instance.steps[4].content, instance.steps[4].is_final_answer)

    