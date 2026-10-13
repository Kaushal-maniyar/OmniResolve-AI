from c360.config import settings

driver = settings.get_driver()

with driver.session(database=settings.database) as session:
    # 1. Collect all tickets connected to C001
    query_find = """
    MATCH (c:Customer) WHERE c.id =~ '(?i)C001'
    OPTIONAL MATCH (c)-[:HAS_TICKET]->(t1:Ticket)
    OPTIONAL MATCH (c)-[:SENT]->(m:Message)-[:ASSOCIATED]->(t2:Ticket)
    WITH collect(DISTINCT t1) + collect(DISTINCT t2) AS c001_tickets
    UNWIND c001_tickets AS t
    WITH t WHERE t IS NOT NULL
    RETURN DISTINCT t.id AS ticket_id
    """
    tickets_to_delete = [row["ticket_id"] for row in session.run(query_find).data()]

    print(f"Found {len(tickets_to_delete)} ticket(s) to delete for customer C001:")
    for tid in tickets_to_delete:
        print(f" - {tid}")

    # 2. Detach delete those tickets
    if tickets_to_delete:
        delete_query = """
        UNWIND $tids AS tid
        MATCH (t:Ticket {id: tid})
        DETACH DELETE t
        """
        session.run(delete_query, tids=tickets_to_delete)
        print("\nAll matching Ticket nodes successfully deleted from Neo4j.")

    # 3. Verify remaining tickets in database
    remaining = session.run("MATCH (t:Ticket) RETURN t.id AS id, properties(t) AS props").data()
    print(f"\nRemaining tickets in database ({len(remaining)}):")
    for r in remaining:
        print(f" - {r['id']}")

    # 4. Verify C001 tickets count
    c001_check = session.run("""
    MATCH (c:Customer) WHERE c.id =~ '(?i)C001'
    OPTIONAL MATCH (c)-[:HAS_TICKET]->(t1:Ticket)
    OPTIONAL MATCH (c)-[:SENT]->(m:Message)-[:ASSOCIATED]->(t2:Ticket)
    RETURN count(t1) + count(t2) AS c001_tickets_count
    """).single()
    print(f"\nTickets connected to C001 count after deletion: {c001_check['c001_tickets_count']}")
