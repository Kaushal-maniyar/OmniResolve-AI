MATCH (c:Customer {customer_id: $customer_id})
RETURN
  c{.customer_id, .name, .email, .phone, .segment, .location, .created_at} AS customer,
  COLLECT { MATCH (c)-[:OWNS]->(p:Product) RETURN p.name ORDER BY p.name } AS owned_products,
  COLLECT {
    MATCH (c)-[:HAS_TICKET]->(t:Ticket)-[:ABOUT]->(p:Product)
    RETURN t{.ticket_id, .status, .priority, .created_at, .resolved_at, .description, product: p.name}
    ORDER BY t.created_at
  } AS tickets,
  COLLECT {
    MATCH (c)-[:HAD_INTERACTION]->(i:Interaction)-[:VIA]->(ch:Channel)
    MATCH (i)-[:HANDLED_BY]->(a:Agent)
    MATCH (i)-[:ABOUT]->(p:Product)
    RETURN i{.interaction_id, .occurred_at, .type, .subject, .sentiment, .summary,
             channel: ch.name, agent: a.name, product: p.name}
    ORDER BY i.occurred_at
  } AS interactions;
