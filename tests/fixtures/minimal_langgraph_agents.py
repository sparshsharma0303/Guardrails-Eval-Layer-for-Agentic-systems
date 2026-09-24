from typing import TypedDict
from langgraph.graph import StateGraph,END

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


if __name__ == "__main__":
    for step_output in app.stream({"user_message": "hello agent"}, stream_mode="updates"):
        print(step_output)

