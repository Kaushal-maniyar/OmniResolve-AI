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
        return {
            "error": "Customer ID or email is required.",
            "owned_products": [],
            "tickets": [],
            "complaints": []
        }

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
                profile["owned_products"] = [
                    f"{p['name']} ({p['id']})" for p in prod_res]

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
        print(
            f"Notice: Neo4j profile lookup skipped ({e}). Returning fallback profile.")
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
    cid = customer_id or ""

    if not mid and not cid:
        return []

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
    customer_id: Optional[str] = None,
    agent_id: Optional[str] = "A003",
    priority: Optional[str] = "High"
) -> Dict[str, Any]:
    """Create a support ticket in Neo4j and confirm only after successful persistence."""

    cid = customer_id

    if not cid:
        return {
            "success": False,
            "id": None,
            "error": "Customer ID is required.",
            "message": "Cannot create a ticket without a customer ID."
        }

    aid = agent_id or "A003"
    prio = priority or "High"

    ticket_id = f"TCK-{uuid.uuid4().hex[:12].upper()}"
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    ticket_data = {
        "id": ticket_id,
        "status": "Escalated to Tier-2",
        "priority": prio,
        "problem_description": problem_description,
        "created_at": now_str
    }

    def create_ticket_transaction(tx):
        query = """
        MATCH (c:Customer {id: $cid})
        MATCH (a:Agent {id: $aid})

        CREATE (t:Ticket {
            id: $tid,
            status: $status,
            priority: $priority,
            problem_description: $desc,
            created_at: $created_at
        })

        SET a:LLMAgent

        MERGE (a)-[:RAISE]->(t)
        MERGE (c)-[:HAS_TICKET]->(t)

        RETURN
            t.id AS id,
            c.id AS customer_id,
            a.id AS agent_id
        """

        result = tx.run(
            query,
            cid=cid,
            aid=aid,
            tid=ticket_id,
            status=ticket_data["status"],
            priority=prio,
            desc=problem_description,
            created_at=now_str
        )

        record = result.single(strict=True)

        return dict(record) if record else None

    driver = settings.get_driver()

    try:
        with driver.session(database=settings.database) as session:
            persisted = session.execute_write(create_ticket_transaction)

        if not persisted:
            raise RuntimeError(
                f"Ticket creation failed: customer {cid} "
                f"or agent {aid} was not found."
            )

        print(f"Neo4j Ticket Persisted: {ticket_id}")

        return {
            "success": True,
            **ticket_data,
            "customer_id": persisted["customer_id"],
            "agent_id": persisted["agent_id"]
        }

    except Exception as e:
        print(f"Neo4j Ticket Creation Failed: {e}")

        return {
            "success": False,
            "id": None,
            "error": str(e),
            "message": (
                "The support ticket could not be created. "
                "Do not tell the customer that a ticket was raised."
            )
        }

    finally:
        driver.close()
