import datetime
from c360.config import settings

driver = settings.get_driver()
now_str = datetime.datetime.now().isoformat()

with driver.session(database=settings.database) as session:
    # 1. Update T001
    session.run("""
        MATCH (c:Customer {id: 'C001'})
        OPTIONAL MATCH (c)-[:SENT]->(m:Message)-[:ASSOCIATED]->(t:Ticket)
        WITH t WHERE t IS NOT NULL
        SET t.status = 'Closed', t.closed_at = $now
    """, now=now_str)

    # 2. Update all TCK- tickets generated for C001
    session.run("""
        MATCH (c:Customer {id: 'C001'})
        MATCH (t:Ticket) WHERE t.id STARTS WITH 'TCK-'
        MERGE (c)-[:HAS_TICKET]->(t)
        SET t.status = 'Closed', t.closed_at = $now
    """, now=now_str)

    # 3. Retrieve all tickets for C001 to verify
    res = session.run("""
        MATCH (c:Customer {id: 'C001'})
        OPTIONAL MATCH (c)-[:SENT]->(m:Message)-[:ASSOCIATED]->(t1:Ticket)
        OPTIONAL MATCH (c)-[:HAS_TICKET]->(t2:Ticket)
        WITH collect(DISTINCT t1) + collect(DISTINCT t2) AS all_tickets
        UNWIND all_tickets AS t
        WITH t WHERE t IS NOT NULL
        RETURN DISTINCT t.id AS id, t.status AS status, t.closed_at AS closed_at, coalesce(t.problem_description, t.problem_des, '') AS desc
    """).data()

print(f"Total tickets closed for Customer C001: {len(res)}")
for row in res:
    print(f" - Ticket {row['id']}: Status = {row['status']}, Closed At = {row['closed_at']}")
