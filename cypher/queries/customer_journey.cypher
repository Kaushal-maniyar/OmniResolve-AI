MATCH (c:Customer {customer_id: $customer_id})-[:HAD_INTERACTION]->(i:Interaction),
      (i)-[:VIA]->(ch:Channel), (i)-[:HANDLED_BY]->(a:Agent), (i)-[:ABOUT]->(p:Product)
RETURN i.interaction_id, i.occurred_at, i.type, i.subject, i.sentiment, i.summary,
       ch.name AS channel, a.name AS agent, p.name AS product
ORDER BY i.occurred_at;
