import uuid
import datetime
from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
from c360.config import settings
from c360.knowledge.retriever import retriever

@tool
def retrive_data_from_Neo4j(customer_id: Optional[str] = "", customer_email: Optional[str] = "") -> Dict[str, Any]:
    """Retrieve Customer 360 profile, active owned products, tickets, and complaints from Neo4j Graph Database."""
    cid = customer_id or ""
    cem = customer_email or ""

    if not cid and not cem:
        # Fallback to C001 for demo testing if customer info omitted
        cid = "C001"

    driver = settings.get_driver()
    profile = {
        "id": cid,
        "email": cem,
        "name": "Valued Customer",
        "owned_products": [],
        "tickets": [],
        "complaints": []
    }

    try:
        with driver.session(database=settings.database) as session:
            # Match Customer Node
            if cid:
                query = "MATCH (c:Customer {id: $cid}) RETURN c.id AS id, c.name AS name, c.email AS email"
                res = session.run(query, cid=cid).single()
            else:
                query = "MATCH (c:Customer {email: $email}) RETURN c.id AS id, c.name AS name, c.email AS email"
                res = session.run(query, email=cem).single()

            if res:
                profile["id"] = res["id"]
                profile["name"] = res["name"]
                profile["email"] = res["email"]

                # Fetch Owned Products
                prod_res = session.run(
                    "MATCH (c:Customer {id: $cid})-[:OWNS]->(p:Product) RETURN p.id AS id, p.name AS name",
                    cid=res["id"]
                ).data()
                profile["owned_products"] = [f"{p['name']} ({p['id']})" for p in prod_res]

                # Fetch Tickets (associated via message or linked directly to customer)
                tkt_query = """
                MATCH (c:Customer {id: $cid})
                OPTIONAL MATCH (c)-[:SENT]->(m:Message)-[:ASSOCIATED]->(t1:Ticket)
                OPTIONAL MATCH (c)-[:HAS_TICKET]->(t2:Ticket)
                WITH collect(DISTINCT t1) + collect(DISTINCT t2) AS all_tickets
                UNWIND (CASE WHEN size(all_tickets) > 0 THEN all_tickets ELSE [null] END) AS t
                WITH t WHERE t IS NOT NULL
                RETURN t.id AS id, t.status AS status, coalesce(t.problem_description, t.problem_des, '') AS desc
                """
                tkt_res = session.run(tkt_query, cid=res["id"]).data()
                profile["tickets"] = tkt_res

                # Fetch Complaints
                cmp_query = """
                MATCH (c:Customer {id: $cid})-[:SENT]->(m:Message)-[:YES]->(cmp:Complaint)
                RETURN cmp.id AS id, cmp.status AS status
                """
                cmp_res = session.run(cmp_query, cid=res["id"]).data()
                profile["complaints"] = cmp_res

    except Exception as e:
        print(f"Notice: Neo4j profile lookup skipped ({e}). Returning fallback profile.")
    finally:
        driver.close()

    return profile

@tool
def retrive_data_from_knowledgebase(query: str, product_id: Optional[str] = "", top_k: int = 15) -> Dict[str, Any]:
    """Retrieve product troubleshooting procedures, FAQs, and diagnostic guides from Vector Store."""
    pid = product_id or None
    return retriever.retrieve(query, product_id=pid, top_k=top_k)

@tool
def retrive_images_or_video(message_id: Optional[str] = "", customer_id: Optional[str] = "") -> List[Dict[str, Any]]:
    """Retrieve image or video attachment metadata linked to customer messages from Neo4j Graph Database."""
    attachments = []
    mid = message_id or ""
    cid = customer_id or "C001"

    driver = settings.get_driver()
    try:
        with driver.session(database=settings.database) as session:
            if mid:
                cypher = """
                MATCH (m:Message {id: $mid})-[:HAS]->(att)
                RETURN labels(att)[0] AS type, att.id AS id, att.path AS path
                """
                res = session.run(cypher, mid=mid).data()
            else:
                cypher = """
                MATCH (c:Customer {id: $cid})-[:SENT]->(m:Message)-[:HAS]->(att)
                RETURN labels(att)[0] AS type, att.id AS id, att.path AS path
                """
                res = session.run(cypher, cid=cid).data()
            attachments = res
    except Exception as e:
        print(f"Notice: Media attachments lookup skipped ({e}).")
    finally:
        driver.close()

    return attachments

@tool
def generate_ticket(
    problem_description: str,
    customer_id: Optional[str] = "C001",
    agent_id: Optional[str] = "A003",
    priority: Optional[str] = "High"
) -> Dict[str, Any]:
    """Create and persist a new formal Support Ticket node in Neo4j Graph Database."""
    cid = customer_id or "C001"
    aid = agent_id or "A003"
    prio = priority or "High"

    ticket_id = f"TCK-{str(uuid.uuid4())[:6].upper()}"
    now_str = datetime.datetime.now().isoformat()
    ticket_data = {
        "id": ticket_id,
        "status": "Escalated to Tier-2",
        "priority": prio,
        "problem_description": problem_description,
        "created_at": now_str
    }

    driver = settings.get_driver()
    try:
        with driver.session(database=settings.database) as session:
            cypher = """
            MERGE (t:Ticket {id: $tid})
            SET t.status = $status, t.problem_description = $desc, t.created_at = $created_at
            WITH t
            MATCH (a:Agent {id: $aid})
            SET a:LLMAgent
            MERGE (a)-[:RAISE {date: $created_at}]->(t)
            WITH t
            MATCH (c:Customer {id: $cid})
            MERGE (c)-[:HAS_TICKET]->(t)
            """
            session.run(cypher, tid=ticket_id, status=ticket_data["status"], desc=problem_description, created_at=now_str, aid=aid, cid=cid)
            print(f"Neo4j Ticket Persisted: Ticket({ticket_id}) -[:RAISES]-> Agent({aid}) & Customer({cid})")
    except Exception as e:
        print(f"Notice: Neo4j ticket node creation skipped ({e}). Local ticket confirmation generated.")
    finally:
        driver.close()

    return ticket_data
