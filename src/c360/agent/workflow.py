from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from c360.agent.state import AgentState
from c360.agent.nodes import (
    add_msg_to_neo4j_node,
    llm_node,
    send_respone_node,
    AGENT_TOOLS
)

# Global in-memory checkpointer for multi-turn conversational state
memory_checkpointer = MemorySaver()


def create_customer_support_graph():
    """Build and compile the LangGraph State Graph workflow following the architectural diagram."""
    builder = StateGraph(AgentState)

    # 1. Add State Graph Nodes
    builder.add_node("add_msg_to_neo4j", add_msg_to_neo4j_node)
    builder.add_node("LLM", llm_node)
    builder.add_node("tools", ToolNode(AGENT_TOOLS))
    builder.add_node("send_respone", send_respone_node)

    # 2. Add State Graph Edges
    builder.add_edge(START, "add_msg_to_neo4j")
    builder.add_edge("add_msg_to_neo4j", "LLM")
    builder.add_conditional_edges("LLM", tools_condition, {
                                  "tools": "tools", END: "send_respone"})
    builder.add_edge("tools", "LLM")
    builder.add_edge("send_respone", END)

    return builder.compile(checkpointer=memory_checkpointer)


# Global compiled LangGraph Customer Support Graph with Memory Checkpointer
CustomerSupportGraph = create_customer_support_graph()


def run_agent_graph(
    message_content: str,
    customer_id: str,
    customer_email: str = None,
    channel: str = "whatsapp",
    thread_id: str = "default_session"
) -> dict:
    """
    Execute the LangGraph customer support workflow
    for an incoming customer message.
    """

    # Prevent execution without a customer ID
    if not customer_id or not customer_id.strip():
        raise ValueError(
            "A customer_id is required to run the customer support agent."
        )

    # Initialize agent state
    initial_state = {
        "message_content": message_content,
        "customer_id": customer_id,
        "customer_email": customer_email,
        "channel": channel,
        "needs_escalation": False,
        "ticket_created": None
    }

    # Maintain separate conversation memory for each thread
    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    # Execute LangGraph workflow
    final_state = CustomerSupportGraph.invoke(
        initial_state,
        config=config
    )

    return final_state
