import datetime
import uuid
from c360.config import settings

def test_pipeline_dry_run():
    cid = "C001"
    aid = "A003"
    now_str = datetime.datetime.now().isoformat()
    m1_id = f"MSG-TEST-{str(uuid.uuid4())[:4].upper()}"
    m2_id = f"MSG-RESP-TEST-{str(uuid.uuid4())[:4].upper()}"
    cmp_id = f"CMP-TEST-{str(uuid.uuid4())[:4].upper()}"

    driver = settings.get_driver()
    with driver.session(database=settings.database) as session:
        # Step 1: Customer sends message complaining about WiFi
        cypher1 = """
        MERGE (c:Customer {id: $cid})
        CREATE (m1:Message {id: $m1_id, date: $now, content: 'My WiFi is down and cannot connect', sent_to: $aid})
        MERGE (c)-[:SENT {date: $now}]->(m1)
        CREATE (cmp:Complaint {id: $cmp_id, status: 'Open', created_at: $now})
        MERGE (cmp)-[:YES]->(m1)
        RETURN m1.id AS mid, cmp.id AS cmp_id
        """
        r1 = session.run(cypher1, cid=cid, aid=aid, m1_id=m1_id, cmp_id=cmp_id, now=now_str).single()
        print("Customer message ingested:", dict(r1))

        # Step 2: Agent sends response
        cypher2 = """
        MERGE (a:Agent {id: $aid})
        SET a:LLMAgent, a.name = 'LLM Agent', a.type = 'LLM'
        CREATE (m2:Message {id: $m2_id, date: $now, content: 'Here are troubleshooting steps for your WiFi', sent_to: $cid})
        MERGE (a)-[:SENT {date: $now}]->(m2)
        WITH m2
        MATCH (m1:Message {id: $m1_id})
        MERGE (m1)-[:NEXT]->(m2)
        MERGE (m2)-[:PRE]->(m1)
        RETURN m2.id AS mid
        """
        r2 = session.run(cypher2, cid=cid, aid=aid, m1_id=m1_id, m2_id=m2_id, now=now_str).single()
        print("Agent response ingested:", dict(r2))

        # Step 3: Verify the graph connections
        verify_cypher = """
        MATCH (c:Customer {id: $cid})-[:SENT]->(m1:Message {id: $m1_id})
        MATCH (cmp:Complaint {id: $cmp_id})-[:YES]->(m1)
        MATCH (m1)-[:NEXT]->(m2:Message {id: $m2_id})
        MATCH (m2)-[:PRE]->(m1)
        MATCH (a:Agent {id: $aid})-[:SENT]->(m2)
        RETURN c.id AS customer, 
               m1.sent_to AS m1_sent_to, 
               cmp.id AS complaint, 
               m2.sent_to AS m2_sent_to, 
               labels(a) AS agent_labels, 
               a.name AS agent_name
        """
        v = session.run(verify_cypher, cid=cid, aid=aid, m1_id=m1_id, m2_id=m2_id, cmp_id=cmp_id).single()
        print("\nGraph Verification Result:")
        print(dict(v))

        # Clean up test nodes
        cleanup = """
        MATCH (m1:Message {id: $m1_id}) DETACH DELETE m1
        WITH 1 AS _
        MATCH (m2:Message {id: $m2_id}) DETACH DELETE m2
        WITH 1 AS _
        MATCH (cmp:Complaint {id: $cmp_id}) DETACH DELETE cmp
        """
        session.run(cleanup, m1_id=m1_id, m2_id=m2_id, cmp_id=cmp_id)
        print("\nCleaned up test nodes successfully.")

if __name__ == "__main__":
    test_pipeline_dry_run()
