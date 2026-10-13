import re
import json
import uuid
import datetime
from typing import Dict, Any, List, Optional
from c360.config import settings
from c360.agent.client import get_chat_model

FAST_NEGATIVE_PATTERNS = [
    r"^\s*(hi|hello|hey|good\s+morning|good\s+afternoon|good\s+evening|hi\s+there)\b",
    r"^\s*how\s+many\s+(open\s+)?tickets?",
    r"^\s*(check|show|what\s+are)\s+(my\s+)?tickets?",
    r"^\s*(what\s+products?|which\s+products?)\s+(do\s+i\s+have|owned)",
    r"^\s*(thank\s+you|thanks|bye|goodbye|ok|okay)\s*$"
]

FAST_POSITIVE_KEYWORDS = [
    "not working", "is down", "stopped working", "disconnected", "disconnecting",
    "slow speed", "slow", "high ping", "packet loss", "los light", "red light",
    "one way audio", "one-way audio", "call drop", "call drops", "registration fail",
    "broken", "complaint", "issue persist", "still not working", "failed to connect",
    "cannot connect", "cant connect", "authentication error", "no internet", "fault",
    "intermittent", "unreachable", "circuit down"
]

def ensure_llm_agent_node(session, agent_id: str = "A003", name: str = "LLM Agent"):
    """Ensure LLM Agent node exists with Agent and LLMAgent labels in Neo4j."""
    cypher = """
    MERGE (a:Agent {id: $aid})
    SET a:LLMAgent, a.name = $name, a.type = 'LLM'
    """
    session.run(cypher, aid=agent_id, name=name)

def classify_message_complaint(text: str) -> bool:
    """Classify if customer message contains a problem report, issue, or complaint about a product."""
    clean = text.strip().lower()
    if not clean:
        return False

    # 1. Fast negative check
    for pat in FAST_NEGATIVE_PATTERNS:
        if re.search(pat, clean):
            return False

    # 2. Fast positive keywords
    for kw in FAST_POSITIVE_KEYWORDS:
        if kw in clean:
            return True

    # 3. LLM classification fallback for nuanced language
    try:
        llm = get_chat_model(temperature=0.0)
        prompt = f"""You are an expert telecommunications customer complaint classifier.
Analyze the customer message and decide if it expresses a complaint, problem report, or malfunction about a product or service.
A greeting or inquiry is NOT a complaint.
Respond with JSON: {{\"is_complaint\": true/false}}

Customer message: "{text}"
"""
        res = llm.invoke(prompt)
        cleaned = res.content.strip().strip("```json").strip("```").strip()
        data = json.loads(cleaned)
        return bool(data.get("is_complaint", False))
    except Exception as e:
        print(f"Notice: LLM complaint classification fallback error ({e}). Defaulting to False.")
        return False

def ingest_customer_message(
    customer_id: str = "C001",
    content: str = "",
    channel: str = "whatsapp",
    attachments: Optional[List[Dict[str, Any]]] = None,
    prev_message_id: Optional[str] = None,
    agent_id: str = "A003"
) -> Dict[str, Any]:
    """
    Ingest customer message into Neo4j graph:
    1. Sets message property sent_to = agent_id.
    2. Maintains conversation sequence via NEXT and PRE edges.
    3. Detects product complaints and links (Complaint)-[:YES]->(Message).
    4. Links attachments (Image/Video) via HAS edges.
    """
    msg_id = f"MSG-{str(uuid.uuid4())[:6].upper()}"
    now_str = datetime.datetime.now().isoformat()
    cid = customer_id or "C001"
    aid = agent_id or "A003"
    chan = channel or "whatsapp"

    # Classify whether this message is a product complaint
    is_complaint = classify_message_complaint(content)
    cmp_id = f"CMP-{str(uuid.uuid4())[:6].upper()}" if is_complaint else None

    driver = settings.get_driver()
    try:
        with driver.session(database=settings.database) as session:
            # 1. Ensure Agent node exists
            ensure_llm_agent_node(session, agent_id=aid)

            # 2. Ingest Message / Email node with sent_to property
            if chan.lower() == "email":
                cypher_msg = """
                MERGE (c:Customer {id: $cid})
                CREATE (e:Email {id: $mid, date: $now, sub: 'Customer Inquiry', body: $content, sent_to: $aid})
                CREATE (c)-[:SENT {date: $now}]->(e)
                CREATE (c)-[:LAST_INTERACTION {date: $now}]->(e)
                """
                session.run(cypher_msg, cid=cid, mid=msg_id, now=now_str, content=content, aid=aid)
            else:
                cypher_msg = """
                MERGE (c:Customer {id: $cid})
                CREATE (m:Message {id: $mid, date: $now, content: $content, sent_to: $aid})
                CREATE (c)-[:SENT {date: $now}]->(m)
                """
                session.run(cypher_msg, cid=cid, mid=msg_id, now=now_str, content=content, aid=aid)

            print(f"Neo4j Persisted Incoming {chan.title()}: Customer({cid}) -[:SENT]-> Message({msg_id}) [sent_to: {aid}]")

            # 3. Maintain conversation sequence via NEXT and PRE edges
            if prev_message_id:
                cypher_seq = """
                MATCH (prev) WHERE prev.id = $prev_id
                MATCH (curr) WHERE curr.id = $curr_id
                MERGE (prev)-[:NEXT]->(curr)
                MERGE (curr)-[:PRE]->(prev)
                """
                session.run(cypher_seq, prev_id=prev_message_id, curr_id=msg_id)
                print(f"Neo4j Sequence Linked: Message({prev_message_id}) <==[NEXT / PRE]==> Message({msg_id})")
            else:
                # If prev_message_id not explicitly provided in memory, link from latest customer/agent interaction
                cypher_auto_seq = """
                MATCH (curr) WHERE curr.id = $curr_id
                OPTIONAL MATCH (c:Customer {id: $cid})-[:SENT]->(last_c) WHERE last_c.id <> $curr_id
                OPTIONAL MATCH (a:Agent {id: $aid})-[:SENT]->(last_a) WHERE last_a.sent_to = $cid AND last_a.id <> $curr_id
                WITH curr, [last_c, last_a] AS candidates
                UNWIND candidates AS cand
                WITH curr, cand WHERE cand IS NOT NULL
                ORDER BY cand.date DESC LIMIT 1
                MERGE (cand)-[:NEXT]->(curr)
                MERGE (curr)-[:PRE]->(cand)
                """
                session.run(cypher_auto_seq, curr_id=msg_id, cid=cid, aid=aid)

            # 4. Create and link Complaint node if complaint detected: (Complaint)-[:YES]->(Message)
            if is_complaint and cmp_id:
                cypher_cmp = """
                MATCH (m) WHERE m.id = $mid
                CREATE (cmp:Complaint {id: $cmp_id, status: 'Open', created_at: $now})
                MERGE (cmp)-[:YES]->(m)
                """
                session.run(cypher_cmp, mid=msg_id, cmp_id=cmp_id, now=now_str)
                print(f"Neo4j Persisted Complaint: Complaint({cmp_id}) -[:YES]-> Message({msg_id})")

            # 5. Link attachments if any: (Message)-[:HAS]->(Image) or (Email)-[:HAS]->(Video)
            if attachments:
                for att in attachments:
                    att_type = att.get("type", "Image").capitalize()
                    att_path = att.get("path", "")
                    att_id = att.get("id") or f"ATT-{str(uuid.uuid4())[:6].upper()}"
                    if att_type.lower() == "video":
                        cypher_att = """
                        MATCH (m) WHERE m.id = $mid
                        CREATE (v:Video {id: $att_id, path: $path})
                        MERGE (m)-[:HAS]->(v)
                        """
                    else:
                        cypher_att = """
                        MATCH (m) WHERE m.id = $mid
                        CREATE (i:Image {id: $att_id, path: $path})
                        MERGE (m)-[:HAS]->(i)
                        """
                    session.run(cypher_att, mid=msg_id, att_id=att_id, path=att_path)
                    print(f"Neo4j Persisted Attachment: Message({msg_id}) -[:HAS]-> {att_type}({att_id})")

    except Exception as e:
        print(f"Notice: Neo4j customer message ingestion notice ({e}).")
    finally:
        driver.close()

    return {
        "message_id": msg_id,
        "is_complaint": is_complaint,
        "complaint_id": cmp_id,
        "sent_to": aid,
        "channel": chan
    }

def ingest_agent_response(
    customer_id: str = "C001",
    content: str = "",
    prev_message_id: Optional[str] = None,
    agent_id: str = "A003",
    ticket_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Ingest AI generated response into Neo4j graph:
    1. Sets message property sent_to = customer_id.
    2. Sends from node LLM Agent (:Agent:LLMAgent).
    3. Maintains conversation sequence: (prev_message)-[:NEXT]->(resp) and (resp)-[:PRE]->(prev_message).
    4. Links Ticket if raised: (Agent)-[:RAISE]->(Ticket) and (prev_message)-[:ASSOCIATED]->(Ticket).
    """
    resp_msg_id = f"MSG-RESP-{str(uuid.uuid4())[:6].upper()}"
    now_str = datetime.datetime.now().isoformat()
    cid = customer_id or "C001"
    aid = agent_id or "A003"

    driver = settings.get_driver()
    try:
        with driver.session(database=settings.database) as session:
            # 1. Ensure LLM Agent node exists
            ensure_llm_agent_node(session, agent_id=aid, name="LLM Agent")

            # 2. Create Response Message node with sent_to property
            cypher_resp = """
            MATCH (a:Agent {id: $aid})
            CREATE (m:Message {id: $mid, date: $now, content: $content, sent_to: $cid})
            CREATE (a)-[:SENT {date: $now}]->(m)
            """
            session.run(cypher_resp, aid=aid, mid=resp_msg_id, now=now_str, content=content[:500], cid=cid)
            print(f"Neo4j Persisted Agent Response: LLMAgent({aid}) -[:SENT]-> Message({resp_msg_id}) [sent_to: {cid}]")

            # 3. Maintain conversation sequence via NEXT and PRE edges
            if prev_message_id:
                cypher_seq = """
                MATCH (prev) WHERE prev.id = $prev_id
                MATCH (resp:Message {id: $resp_id})
                MERGE (prev)-[:NEXT]->(resp)
                MERGE (resp)-[:PRE]->(prev)
                """
                session.run(cypher_seq, prev_id=prev_message_id, resp_id=resp_msg_id)
                print(f"Neo4j Sequence Linked: Message({prev_message_id}) <==[NEXT / PRE]==> Message({resp_msg_id})")

            # 4. If a ticket was created, link (Agent)-[:RAISE]->(Ticket) and (Message)-[:ASSOCIATED]->(Ticket)
            if ticket_id:
                cypher_tkt = """
                MATCH (a:Agent {id: $aid})
                MATCH (t:Ticket {id: $tid})
                MERGE (a)-[:RAISE {date: $now}]->(t)
                WITH t, $prev_id AS pid
                MATCH (prev) WHERE prev.id = pid
                MERGE (prev)-[:ASSOCIATED]->(t)
                """
                session.run(cypher_tkt, aid=aid, tid=ticket_id, now=now_str, prev_id=prev_message_id)
                print(f"Neo4j Ticket Linked: Agent({aid}) -[:RAISE]-> Ticket({ticket_id}) & Message({prev_message_id}) -[:ASSOCIATED]-> Ticket({ticket_id})")

    except Exception as e:
        print(f"Notice: Neo4j agent response ingestion notice ({e}).")
    finally:
        driver.close()

    return {
        "response_message_id": resp_msg_id,
        "agent_id": aid,
        "sent_to": cid
    }
