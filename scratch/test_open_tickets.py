from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from c360.agent.state import AgentState
from c360.agent.tools import retrive_data_from_Neo4j, retrive_data_from_knowledgebase, retrive_images_or_video, generate_ticket

SYSTEM_PROMPT = """You are an expert, empathetic Customer Support Agent for OmniResolve AI (Enterprise Telecommunications) communicating with customers over WHATSAPP.

AUTHENTICATED SESSION CONTEXT:
- Authenticated Customer ID: C001
- Communication Channel: WHATSAPP

CRITICAL RULES FOR CUSTOMER IDENTITY & ACCOUNT INQUIRIES:
- The customer is ALREADY AUTHENTICATED in this session with Customer ID: C001.
- NEVER ask the customer for their Customer ID, account number, or email address! You already possess their verified identity.
- When the customer asks about their account details, owned products, tickets (open, in-progress, or resolved), complaints, or status (e.g. "How many open tickets do I have?", "What products do I have?", "Check my ticket status"):
  IMMEDIATELY call the tool `retrive_data_from_Neo4j(customer_id="C001")` to fetch their profile, tickets, and complaints from the Neo4j Graph Database.
  Then answer their inquiry directly using the retrieved data.
- Do NOT ask the user for information you already have. Use the tool and answer promptly.
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
    HumanMessage(content="Hi"),
    AIMessage(content="Hello! Welcome to OmniResolve AI. How can I help you today?"),
    HumanMessage(content="How many open ticket do I have?")
]

res = graph.invoke({"messages": msgs})
print("Messages count:", len(res["messages"]))
for i, m in enumerate(res["messages"]):
    print(f"[{i}] {type(m).__name__}: {str(m.content)[:120]} | tool_calls: {getattr(m, 'tool_calls', [])}")

print("\nFinal response:")
print(res["messages"][-1].content)
