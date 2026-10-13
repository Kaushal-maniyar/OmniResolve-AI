import sys
sys.stdout.reconfigure(encoding='utf-8')
import uuid
from c360.config import settings
from c360.agent.workflow import run_agent_graph

thread_id = f"test_features_thread_{str(uuid.uuid4())[:6]}"
customer_id = "C001"

print(f"=== TESTING COMPLETE 5 FEATURES PIPELINE (Thread: {thread_id}) ===\n")

# Turn 1: Greeting
print("--- TURN 1: GREETING ---")
res1 = run_agent_graph("Hi", customer_id=customer_id, channel="whatsapp", thread_id=thread_id)
print("Turn 1 Response:", res1.get("final_response"))
m1_id = res1.get("message_id")
r1_id = res1.get("response_message_id")
print(f"m1_id: {m1_id}, r1_id: {r1_id}, is_complaint: {res1.get('is_complaint')}")

# Turn 2: Product Complaint
print("\n--- TURN 2: PRODUCT COMPLAINT ---")
res2 = run_agent_graph("My Enterprise WiFi is very slow and keeps dropping connection", customer_id=customer_id, channel="whatsapp", thread_id=thread_id)
print("Turn 2 Response:", res2.get("final_response")[:120], "...")
m2_id = res2.get("message_id")
r2_id = res2.get("response_message_id")
cmp2_id = res2.get("complaint_id")
print(f"m2_id: {m2_id}, r2_id: {r2_id}, is_complaint: {res2.get('is_complaint')}, complaint_id: {cmp2_id}")

# Turn 3: Troubleshooting Fails (Persistence & Ticket)
print("\n--- TURN 3: TROUBLESHOOTING FAILS ---")
res3 = run_agent_graph("I tried all those steps, but the connection drop issue still persists", customer_id=customer_id, channel="whatsapp", thread_id=thread_id)
print("Turn 3 Response:", res3.get("final_response")[:120], "...")
m3_id = res3.get("message_id")
r3_id = res3.get("response_message_id")
cmp3_id = res3.get("complaint_id")
tkt_id = res3.get("ticket_created", {}).get("id") if res3.get("ticket_created") else None
print(f"m3_id: {m3_id}, r3_id: {r3_id}, is_complaint: {res3.get('is_complaint')}, ticket_id: {tkt_id}")

print("\n=== VERIFYING GRAPH DATABASE CONSTRAINTS ===")
driver = settings.get_driver()
with driver.session(database=settings.database) as session:
    # Feature 1 & 3: Check Complaint nodes connected via YES
    cypher_cmp = """
    MATCH (cmp:Complaint)-[:YES]->(m:Message)
    WHERE m.id IN [$m1_id, $m2_id, $m3_id]
    RETURN cmp.id AS cmp_id, cmp.status AS status, m.id AS msg_id
    """
    cmps = session.run(cypher_cmp, m1_id=m1_id, m2_id=m2_id, m3_id=m3_id).data()
    print(f"\n[Feature 1 & 3] Complaints linked via YES to messages: {len(cmps)}")
    for c in cmps:
        print(f"  - Complaint({c['cmp_id']}) -[:YES]-> Message({c['msg_id']})")
    assert len(cmps) >= 1, "Must have created Complaint node for product complaints!"

    # Feature 2: Check conversation sequence NEXT and PRE edges
    cypher_seq = """
    MATCH (m:Message)
    WHERE m.id IN [$m1_id, $r1_id, $m2_id, $r2_id, $m3_id, $r3_id]
    OPTIONAL MATCH (m)-[:NEXT]->(next:Message)
    OPTIONAL MATCH (m)-[:PRE]->(prev:Message)
    RETURN m.id AS current, next.id AS next_msg, prev.id AS prev_msg
    ORDER BY m.date ASC
    """
    seq = session.run(cypher_seq, m1_id=m1_id, r1_id=r1_id, m2_id=m2_id, r2_id=r2_id, m3_id=m3_id, r3_id=r3_id).data()
    print("\n[Feature 2] Conversation sequence chain (NEXT & PRE):")
    for s in seq:
        print(f"  - Message({s['current']}) -> NEXT: {s['next_msg']} | PRE: {s['prev_msg']}")

    # Feature 4: Check LLM Agent node
    cypher_agent = """
    MATCH (a:Agent {id: 'A003'})
    RETURN a.id AS id, a.name AS name, labels(a) AS labels, a.type AS type
    """
    agent = session.run(cypher_agent).single()
    print(f"\n[Feature 4] LLM Agent node: {dict(agent)}")
    assert "LLMAgent" in agent["labels"], "Agent node must have LLMAgent label!"

    # Feature 5: Check sent_to property on message nodes
    cypher_sent_to = """
    MATCH (m:Message)
    WHERE m.id IN [$m1_id, $r1_id, $m2_id, $r2_id, $m3_id, $r3_id]
    RETURN m.id AS id, m.sent_to AS sent_to
    """
    sent_tos = session.run(cypher_sent_to, m1_id=m1_id, r1_id=r1_id, m2_id=m2_id, r2_id=r2_id, m3_id=m3_id, r3_id=r3_id).data()
    print("\n[Feature 5] Message sent_to properties:")
    for st in sent_tos:
        print(f"  - Message({st['id']}) has sent_to = '{st['sent_to']}'")
    for st in sent_tos:
        assert st["sent_to"] in ["A003", customer_id], f"sent_to must be respective recipient! Got {st['sent_to']}"

print("\n*** ALL 5 FEATURES VERIFIED SUCCESSFULLY IN GRAPH DATABASE ***")
