"""Customer support graph with a ticket-confirmation safety gate."""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import AIMessage, ToolMessage
from c360.agent.state import AgentState
from c360.agent.nodes import (
    add_msg_to_neo4j_node, llm_node, send_respone_node, AGENT_TOOLS
)

memory_checkpointer = MemorySaver()
_tool_node = ToolNode(AGENT_TOOLS)


def confirmed_tools_node(state: AgentState):
    """Reject ticket creation unless the current user explicitly confirms it.

    Other tools work normally. The customer must send CONFIRM TICKET in a
    separate message after the agent proposes a ticket. This is a demo gate,
    not a production-grade authorization mechanism.
    """
    messages = state.get("messages", [])
    last = messages[-1] if messages else None
    calls = getattr(last, "tool_calls", None) or []
    if not any(c.get("name") == "generate_ticket" for c in calls):
        return _tool_node.invoke(state)
    confirmed = (state.get("message_content") or "").strip().upper() == "CONFIRM TICKET"
    if not confirmed:
        # Block the whole tool batch so a mixed call cannot create a ticket.
        return {"messages": [ToolMessage(
            content=("Ticket NOT created. Before creating a support ticket, "
                     "describe the proposed ticket to the customer and ask them "
                     "to reply exactly CONFIRM TICKET. Do not claim it was submitted."),
            tool_call_id=call["id"], name=call["name"]
        ) for call in calls]}
    # ToolNode may receive additional calls alongside the confirmed ticket.
    return _tool_node.invoke(state)


def create_customer_support_graph():
    builder = StateGraph(AgentState)
    builder.add_node("add_msg_to_neo4j", add_msg_to_neo4j_node)
    builder.add_node("LLM", llm_node)
    builder.add_node("tools", confirmed_tools_node)
    builder.add_node("send_respone", send_respone_node)
    builder.add_edge(START, "add_msg_to_neo4j")
    builder.add_edge("add_msg_to_neo4j", "LLM")
    builder.add_conditional_edges("LLM", tools_condition,
                                  {"tools": "tools", END: "send_respone"})
    builder.add_edge("tools", "LLM")
    builder.add_edge("send_respone", END)
    return builder.compile(checkpointer=memory_checkpointer)


CustomerSupportGraph = create_customer_support_graph()


def run_agent_graph(message_content: str, customer_id: str,
                    customer_email: str = None, channel: str = "whatsapp",
                    thread_id: str = "default_session") -> dict:
    if not customer_id or not customer_id.strip():
        raise ValueError("A customer_id is required")
    initial_state = {
        "message_content": message_content,
        "customer_id": customer_id,
        "customer_email": customer_email,
        "channel": channel,
        "needs_escalation": False,
        "ticket_created": None,
    }
    return CustomerSupportGraph.invoke(
        initial_state, config={"configurable": {"thread_id": thread_id}}
    )
