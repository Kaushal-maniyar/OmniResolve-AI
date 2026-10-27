import json
import datetime
import uuid
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from c360.config import settings
from c360.agent.state import AgentState
from c360.agent.client import get_chat_model, create_provider_model
from c360.agent.prompts import get_system_prompt
from c360.graph.ingestion import ingest_customer_message, ingest_agent_response
from c360.agent.tools import (
    retrive_data_from_Neo4j,
    retrive_data_from_knowledgebase,
    retrive_images_or_video,
    generate_ticket
)

AGENT_TOOLS = [
    retrive_data_from_Neo4j,
    retrive_data_from_knowledgebase,
    retrive_images_or_video,
    generate_ticket
]

# Initialize tool-bound ChatOpenAI model
chat_model = get_chat_model().bind_tools(AGENT_TOOLS)

fallback_model = None

if settings.llm_fallback_provider != "none":
    if settings.llm_fallback_provider != settings.llm_provider:
        fallback_model = create_provider_model(
            settings.llm_fallback_provider,
            timeout=30.0
        ).bind_tools(AGENT_TOOLS)


def add_msg_to_neo4j_node(state: AgentState) -> Dict[str, Any]:
    """Node 1: Ingest incoming Customer Message or Email using Message Ingestion Pipeline."""
    msg_content = state.get("message_content", "")

    customer_id = state.get("customer_id")

    if not customer_id:
        raise ValueError(
            "Cannot process customer-specific messages without a customer ID."
        )

    channel = state.get("channel", "whatsapp")
    customer_email = state.get("customer_email")
    attachments = state.get("attachments")
    prev_msg_id = state.get(
        "response_message_id") or state.get("prev_message_id")

    # Ingest incoming message into Neo4j graph via Message Ingestion Pipeline
    ingest_res = ingest_customer_message(
        customer_id=customer_id,
        content=msg_content,
        channel=channel,
        attachments=attachments,
        prev_message_id=prev_msg_id,
        agent_id="A003"
    )
    msg_id = ingest_res["message_id"]
    is_complaint = ingest_res["is_complaint"]
    complaint_id = ingest_res["complaint_id"]

    # Build messages list: Ensure system prompt carries authenticated session context
    system_prompt_text = get_system_prompt(
        customer_id=customer_id,
        channel=channel,
        customer_email=customer_email
    )

    new_messages = [
        SystemMessage(content=system_prompt_text, id="system_instruction")
    ]

    if msg_content:
        new_messages.append(HumanMessage(content=msg_content))

    return {
        "message_id": msg_id,
        "prev_message_id": prev_msg_id,
        "is_complaint": is_complaint,
        "complaint_id": complaint_id,
        "customer_id": customer_id,
        "customer_email": customer_email,
        "channel": channel,
        "messages": new_messages
    }


def llm_node(state: AgentState) -> Dict[str, Any]:
    """Execute agent reasoning using the configured LLM provider."""

    messages = state.get("messages", [])

    try:
        response = chat_model.invoke(messages)
        return {"messages": [response]}

    except Exception as primary_error:
        print(
            f"Primary LLM ({settings.llm_provider}) failed: "
            f"{primary_error}"
        )

        if fallback_model is None:
            raise RuntimeError(
                f"LLM provider '{settings.llm_provider}' is unavailable."
            ) from primary_error

        try:
            response = fallback_model.invoke(messages)
            return {"messages": [response]}

        except Exception as fallback_error:
            raise RuntimeError(
                "Both primary and fallback LLM providers failed."
            ) from fallback_error


def send_respone_node(state: AgentState) -> Dict[str, Any]:
    """Node 3: Ingest Agent Response using Message Ingestion Pipeline & Output Final Result."""
    messages = state.get("messages", [])
    final_text = ""
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.content:
            final_text = str(m.content)
            break

    # Scan for any tickets created or knowledge retrieved during this session
    ticket_created = None
    needs_escalation = False
    product_id = state.get("product_id")

    for m in messages:
        if isinstance(m, ToolMessage):
            # Check for generate_ticket
            if getattr(m, "name", "") == "generate_ticket":
                try:
                    data = json.loads(m.content) if isinstance(
                        m.content, str) else m.content

                    if (
                        isinstance(data, dict)
                        and data.get("success") is True
                        and isinstance(data.get("id"), str)
                        and data["id"].startswith("TCK-")
                    ):
                        ticket_created = data
                        needs_escalation = True

                except (json.JSONDecodeError, TypeError):
                    pass

          # Check for product filter in KB retrieve
            if getattr(m, "name", "") == "retrive_data_from_knowledgebase":
                try:
                    kb_data = json.loads(m.content) if isinstance(
                        m.content, str) else m.content
                    if isinstance(kb_data, dict):
                        detected = kb_data.get("applied_filters", {}).get(
                            "product") or kb_data.get("product_context", {}).get("product_id")
                        if detected:
                            product_id = detected
                except Exception:
                    pass

    customer_id = state.get("customer_id")

    if not customer_id:
        raise ValueError(
            "Cannot process customer-specific messages without a customer ID."
        )
    incoming_msg_id = state.get("message_id")
    ticket_id = ticket_created.get("id") if ticket_created else None

    # Ingest Agent Response into Neo4j via Message Ingestion Pipeline
    resp_ingest = ingest_agent_response(
        customer_id=customer_id,
        content=final_text,
        prev_message_id=incoming_msg_id,
        agent_id="A003",
        ticket_id=ticket_id
    )
    resp_msg_id = resp_ingest["response_message_id"]

    return {
        "final_response": final_text,
        "response_message_id": resp_msg_id,
        "ticket_created": ticket_created,
        "needs_escalation": needs_escalation,
        "product_id": product_id
    }
