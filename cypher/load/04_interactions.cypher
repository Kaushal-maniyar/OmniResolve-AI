UNWIND $rows AS row
MATCH (c:Customer    {customer_id: row.customer_id})
MATCH (ch:Channel    {channel_id:  row.channel_id})
MATCH (a:Agent       {agent_id:    row.agent_id})
MATCH (p:Product     {product_id:  row.product_id})
MERGE (i:Interaction {interaction_id: row.interaction_id})
SET i.type = row.type, i.occurred_at = datetime(row.occurred_at),
    i.subject = row.subject, i.sentiment = row.sentiment, i.summary = row.summary
MERGE (c)-[:HAD_INTERACTION]->(i)
MERGE (i)-[:VIA]->(ch)
MERGE (i)-[:HANDLED_BY]->(a)
MERGE (i)-[:ABOUT]->(p);
