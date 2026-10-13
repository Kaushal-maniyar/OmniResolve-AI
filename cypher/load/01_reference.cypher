UNWIND $agents AS row
MERGE (a:Agent {agent_id: row.agent_id})
SET a.name = row.name, a.team = row.team;

UNWIND $channels AS row
MERGE (ch:Channel {channel_id: row.channel_id})
SET ch.name = row.name;

UNWIND $products AS row
MERGE (p:Product {product_id: row.product_id})
SET p.name = row.name, p.category = row.category;
