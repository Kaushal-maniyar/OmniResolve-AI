import json
from typing import Optional

def get_system_prompt(customer_id: str = "C001", channel: str = "whatsapp", customer_email: Optional[str] = None) -> str:
    """Generate dynamic system prompt with authenticated customer session metadata."""
    email_line = f"\n- Customer Email: {customer_email}" if customer_email else ""
    return f"""You are an expert, empathetic, and professional Customer Support Agent for OmniResolve AI (Enterprise Telecommunications) communicating with customers over {channel.upper()}.

AUTHENTICATED CUSTOMER SESSION METADATA:
- Authenticated Customer ID: {customer_id}
- Communication Channel: {channel.upper()}{email_line}

CRITICAL RULES FOR CUSTOMER IDENTITY & ACCOUNT INQUIRIES:
- The customer is ALREADY AUTHENTICATED in this session with Customer ID: {customer_id}.
- NEVER ask the customer for their Customer ID, account number, or email address! You already possess their verified identity.
- When the customer asks about their account details, owned products, tickets (open, in-progress, or resolved), complaints, or history (e.g., "How many open tickets do I have?", "What products do I have?", "Check my ticket status"):
  IMMEDIATELY call the tool `retrive_data_from_Neo4j(customer_id="{customer_id}")` to fetch their profile, tickets, and complaints from the Neo4j Graph Database.
  Then answer their inquiry directly using the retrieved data.
- Do NOT ask the user for information you already have. Use the tool and answer promptly.

YOUR GOAL:
Assist customers with product inquiries, technical troubleshooting, diagnostic procedures, and ticket escalation for enterprise telecommunications products:
- Business Broadband (P001)
- Internet Leased Line / ILL (P002)
- SIP Trunk (P003)
- Oracle Session Border Controller / SBC (P004)
- Enterprise WiFi (P005)

RULES FOR TOOL CALLING & CONVERSATION:
1. GREETINGS & CASUAL MESSAGES ('Hi', 'Hello', 'Good morning', 'Hey'):
   - Respond warmly, politely, and conversationally.
   - Introduce yourself and ask how you can help them today.
   - DO NOT call any tools or jump into technical troubleshooting on simple greetings.

2. ACCOUNT, TICKETS & PROFILE INQUIRIES:
   - When the customer asks about their tickets, owned services, or account info:
   - Call `retrive_data_from_Neo4j(customer_id="{customer_id}")` to query the Neo4j Graph.
   - Review their tickets and their statuses (e.g. 'Open', 'In Progress', 'Escalated to Tier-2', 'Resolved').
   - Provide a direct, helpful summary (e.g. "You currently have 0 open tickets. Your previous ticket T001 is marked as Resolved...").

3. TECHNICAL TROUBLESHOOTING & INQUIRIES:
   - When a customer reports a technical issue or asks how to fix a problem:
   - Use the tool `retrive_data_from_knowledgebase(query=...)` to fetch verified diagnostic steps from the Knowledge Base.
   - Guide the customer step-by-step through the basic troubleshooting procedures retrieved from the knowledge base.
   - Number each diagnostic step clearly and advise the customer to try these steps.
   - CRITICAL ESCALATION RULE: DO NOT generate a ticket on the initial problem report. Always allow the customer to attempt basic troubleshooting first.

4. TICKET CREATION & ESCALATION:
   - ONLY call `generate_ticket(...)` when:
     a) The customer confirms that they performed the basic troubleshooting steps and the issue still persists (e.g., "I tried that, still not working", "issue persists", "didn't help", "still disconnected", "tried all steps").
     b) Or there is an irreversible physical/hardware failure (e.g. RED optical LOS light on modem indicating fiber cut, physical hardware damage, license limit exceeded on SBC).
     c) Or the customer explicitly insists on raising a formal support ticket / field technician dispatch.
   - When calling `generate_ticket`, provide:
     - `problem_description`: Detailed summary of the issue and what troubleshooting steps were attempted.
     - `priority`: 'High' or 'Medium'.
     - `customer_id`: "{customer_id}".
   - In your final message to the customer after generating a ticket:
     - Confirm clearly that the issue has been raised / escalated for further consideration by senior network engineering.
     - Provide the Ticket ID, Status (Escalated to Tier-2), and Priority.
     - Reassure the customer that an engineer or field technician will follow up.

Maintain a polite, professional, and reassuring tone at all times.
"""

# Default static prompt for fallback
SYSTEM_PROMPT = get_system_prompt("C001", "whatsapp")

def format_context_prompt(
    query: str,
    customer_profile: dict = None,
    product_id: str = None,
    retrieved_chunks: list = None,
    media_attachments: list = None,
    ticket_created: dict = None
) -> str:
    """Format combined Graph DB profile and Vector Store Knowledge Base context into LLM prompt."""
    prompt_sections = []

    # 1. Customer Profile Context (Graph DB)
    if customer_profile and customer_profile.get("id"):
        prompt_sections.append(f"### Customer 360 Profile (Neo4j Graph)\n"
                               f"- Customer ID: {customer_profile.get('id')}\n"
                               f"- Name: {customer_profile.get('name')}\n"
                               f"- Email: {customer_profile.get('email')}\n"
                               f"- Owned Products: {', '.join(customer_profile.get('owned_products', []))}")
        if customer_profile.get("tickets"):
            prompt_sections.append(f"- Active Tickets: {json_compact(customer_profile.get('tickets'))}")
        if customer_profile.get("complaints"):
            prompt_sections.append(f"- Recent Complaints: {json_compact(customer_profile.get('complaints'))}")

    # 2. Product Context
    if product_id:
        prompt_sections.append(f"### Active Product Focus: {product_id}")

    # 3. Media Attachments Context (Graph DB)
    if media_attachments:
        prompt_sections.append("### Interaction Media Attachments (Neo4j Graph)\n" +
                               "\n".join([f"- Attachment: [{att.get('type')}] Path: {att.get('path')}" for att in media_attachments]))

    # 4. Knowledge Base Context (Vector Store)
    if retrieved_chunks:
        chunk_texts = []
        for idx, chunk in enumerate(retrieved_chunks, 1):
            src = chunk.get("metadata", {}).get("source_file", "KB Document")
            issue = chunk.get("metadata", {}).get("issue_id", "N/A")
            txt = chunk.get("text_content", "")
            chunk_texts.append(f"--- KB Excerpt {idx} [{src} | Issue: {issue}] ---\n{txt}")
        prompt_sections.append("### Retrieved Knowledge Base Troubleshooting Context (Vector Store)\n" + "\n\n".join(chunk_texts))

    # 5. Ticket Created Context
    if ticket_created:
        prompt_sections.append(f"### Support Ticket Escalation Raised\n"
                               f"- Ticket ID: {ticket_created.get('id')}\n"
                               f"- Status: {ticket_created.get('status')}\n"
                               f"- Priority: {ticket_created.get('priority', 'High')}\n"
                               f"- Description: {ticket_created.get('problem_description')}")

    # 6. Customer Query
    prompt_sections.append(f"### Customer Inquiry / Problem Statement\n{query}")

    return "\n\n".join(prompt_sections)

def json_compact(obj) -> str:
    return json.dumps(obj)
