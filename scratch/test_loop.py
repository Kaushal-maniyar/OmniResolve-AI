from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from c360.agent.state import AgentState
from c360.agent.tools import retrive_data_from_Neo4j, retrive_data_from_knowledgebase, retrive_images_or_video, generate_ticket

SYSTEM_PROMPT = """You are an expert, empathetic Customer Support Agent for OmniResolve AI (Enterprise Telecommunications) communicating over WhatsApp.

CONVERSATION & TOOL RULES:
1. GREETINGS & CASUAL CHAT ('Hi', 'Hello'):
   - Respond warmly and conversationally without calling tools.
2. TECHNICAL ISSUES & INQUIRIES:
   - Call retrive_data_from_knowledgebase to find verified troubleshooting procedures.
   - Explain the basic troubleshooting steps clearly and ask the customer to try them.
   - NEVER call generate_ticket on the first complaint!
3. ISSUE PERSISTS / ESCALATION:
   - ONLY call generate_ticket if the customer reports that troubleshooting failed ('tried that', 'issue persists', 'still not working') or explicitly asks to raise a ticket.
   - After generating a ticket, provide the ticket ID and confirm escalation to senior engineers.
"""

tools = [retrive_data_from_Neo4j, retrive_data_from_knowledgebase, retrive_images_or_video, generate_ticket]
llm = ChatOpenAI(
    base_url="http://192.168.100.10:8000/v1",
    api_key="llm-engineer-dev-key-change-in-prod",
    model="qwen3.8-27b",
    temperature=0.1,
    timeout=60.0
).bind_tools(tools)

def llm_node(state):
    return {"messages": [llm.invoke(state["messages"])]}

builder = StateGraph(AgentState)
builder.add_node("LLM", llm_node)
builder.add_node("tools", ToolNode(tools))
builder.add_edge(START, "LLM")
builder.add_conditional_edges("LLM", tools_condition, {"tools": "tools", END: END})
builder.add_edge("tools", "LLM")
graph = builder.compile()

msgs = [
    SystemMessage(content=SYSTEM_PROMPT),
    HumanMessage(content="My Enterprise WiFi is not connecting and gives authentication error")
]
res = graph.invoke({"messages": msgs})
print("Number of messages after graph invoke:", len(res["messages"]))
for i, m in enumerate(res["messages"]):
    print(f"[{i}] {type(m).__name__}: {str(m.content)[:120]} | tool_calls: {getattr(m, 'tool_calls', [])}")

import sys
sys.stdout.reconfigure(encoding='utf-8')

# Turn 3: User replies that the issue persists
turn3_msgs = list(res["messages"]) + [
    HumanMessage(content="I tried all those steps, but the authentication error still persists and I still cannot connect.")
]
res3 = graph.invoke({"messages": turn3_msgs})
print("\n--- TURN 3 MESSAGES ---")
for i, m in enumerate(res3["messages"]):
    print(f"[{i}] {type(m).__name__}: {str(m.content)[:120]} | tool_calls: {getattr(m, 'tool_calls', [])}")

print("\nFinal Assistant Output (Turn 3):")
print(res3["messages"][-1].content)

