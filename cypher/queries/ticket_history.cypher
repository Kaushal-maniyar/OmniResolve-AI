MATCH (c:Customer {customer_id: $customer_id})-[:HAS_TICKET]->(t:Ticket)-[:ABOUT]->(p:Product)
MATCH (t)-[:GENERATED_FROM]->(i:Interaction)
RETURN t.ticket_id, t.status, t.priority, t.created_at, t.resolved_at,
       p.name AS product, i.interaction_id AS source_interaction, i.subject AS originating_subject
ORDER BY t.created_at;
