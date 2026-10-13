UNWIND $rows AS row
MATCH (c:Customer    {customer_id: row.customer_id})
MATCH (p:Product     {product_id:  row.product_id})
MATCH (i:Interaction {interaction_id: row.source_interaction_id})
MERGE (t:Ticket {ticket_id: row.ticket_id})
SET t.status = row.status, t.priority = row.priority,
    t.created_at  = datetime(row.created_at),
    t.resolved_at = CASE WHEN row.resolved_at IS NULL OR row.resolved_at = '' THEN null ELSE datetime(row.resolved_at) END,
    t.description = row.description
MERGE (c)-[:HAS_TICKET]->(t)
MERGE (t)-[:GENERATED_FROM]->(i)
MERGE (t)-[:ABOUT]->(p);
