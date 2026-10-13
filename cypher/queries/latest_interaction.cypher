MATCH (c:Customer {customer_id: $customer_id})-[:HAD_INTERACTION]->(last:Interaction)
WHERE NOT (last)-[:NEXT]->()
OPTIONAL MATCH (prev:Interaction)-[:NEXT]->(last)
RETURN last{.interaction_id, .occurred_at, .type, .subject, .sentiment} AS latest,
       prev{.interaction_id, .occurred_at, .type, .subject, .sentiment} AS previous;
