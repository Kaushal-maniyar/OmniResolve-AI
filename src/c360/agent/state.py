from typing import Annotated, TypedDict, Optional, List, Dict, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """LangGraph Agent State schema tracking AWS CDS fields, messages, and retrieved context."""
    # Conversation Messages (LangGraph message history reducer)
    messages: Annotated[List[BaseMessage], add_messages]

    # Incoming Customer & Channel Metadata (Fields from AWS CDS / Webhook)
    customer_id: Optional[str]
    customer_email: Optional[str]
    channel: str  # "whatsapp" or "email"
    message_content: str
    message_id: Optional[str]
    prev_message_id: Optional[str]
    response_message_id: Optional[str]
    attachments: Optional[List[Dict[str, Any]]]

    # Complaint & Sequence Metadata
    is_complaint: Optional[bool]
    complaint_id: Optional[str]

    # Inferred or Linked Product & Context
    product_id: Optional[str]
    customer_profile: Optional[Dict[str, Any]]
    retrieved_chunks: Optional[List[Dict[str, Any]]]
    media_attachments: Optional[List[Dict[str, Any]]]
    
    # Escalation & Ticket Status
    needs_escalation: bool
    ticket_created: Optional[Dict[str, Any]]

    # Final Generated Output
    final_response: str
