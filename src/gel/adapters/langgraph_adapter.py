from gel.schema.trace import Trace, TraceMetaData, AgentMessageStep,ToolCallStep, RetrievedDocument,RetrievalStep,LLMCallStep
from datetime import datetime,timezone
from typing import TypedDict
from langgraph.graph import StateGraph,END



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
        else :
            steps.append(AgentMessageStep(step_index=index,timestamp_start=datetime.now(timezone.utc),content=str(changes)))
    trace = Trace(metadata=metadata, steps= steps)
    return trace


if __name__ == "__main__":
        
    class AgentState(TypedDict):
        user_message: str
        summary:str
        agent_response :str
        tool_name : str
        tool_args: dict
        tool_result: str
        query: str
        retrieved_docs: list
        prompt:str
        completion: str

    def call_llm(state : AgentState)->dict:
        return{"prompt":"decide what to do next", "completion":"I should look up the weather"}


    def retrieve(state: AgentState) -> dict:
        return {"query": "weather lookup method", "retrieved_docs": [{"doc_id": "d1", "content": "Use the weather API for city lookups."}]}

    def call_tool(state :AgentState) -> dict:
        return {"tool_name":"lookup_weather","tool_args":{"city":"Indore"},"tool_result":"sunny, 31c"}

    def respond(state: AgentState)->dict:
        return {"agent_response": "this is a fixed text response"}

    def summarize(state: AgentState)-> dict:
        return {"summary":"response was generated"}


    graph = StateGraph(AgentState)
    graph.add_node("respond",respond)
    graph.add_node("call_tool_node",call_tool)
    graph.add_node("summarize",summarize)
    graph.add_node("retrieve",retrieve)
    graph.add_node("llm_call", call_llm)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve","llm_call")
    graph.add_edge("llm_call","call_tool_node")
    graph.add_edge("call_tool_node","respond")
    graph.add_edge("respond","summarize")
    graph.add_edge("summarize",END)
    app = graph.compile()

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

    