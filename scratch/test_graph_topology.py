from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from c360.agent.state import AgentState
from c360.agent.tools import retrive_data_from_Neo4j, retrive_data_from_knowledgebase, retrive_images_or_video, generate_ticket

tools = [retrive_data_from_Neo4j, retrive_data_from_knowledgebase, retrive_images_or_video, generate_ticket]

def add_msg_to_neo4j(state):
    print("Executed: add_msg_to_neo4j")
    return {"messages": [HumanMessage(content=state.get("message_content", ""))]}

def llm_node(state):
    print("Executed: LLM")
    return {"messages": [AIMessage(content="Hello from test!")]}

def send_respone(state):
    print("Executed: send_respone")
    return {"final_response": state["messages"][-1].content}

builder = StateGraph(AgentState)
builder.add_node("add_msg_to_neo4j", add_msg_to_neo4j)
builder.add_node("LLM", llm_node)
builder.add_node("tools", ToolNode(tools))
builder.add_node("send_respone", send_respone)

builder.add_edge(START, "add_msg_to_neo4j")
builder.add_edge("add_msg_to_neo4j", "LLM")
builder.add_conditional_edges("LLM", tools_condition, {"tools": "tools", END: "send_respone"})
builder.add_edge("tools", "LLM")
builder.add_edge("send_respone", END)

graph = builder.compile()

res = graph.invoke({"message_content": "Hi", "messages": []})
print("Final response:", res["final_response"])
