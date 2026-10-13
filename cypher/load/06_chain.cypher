MATCH ()-[n:NEXT]->() DELETE n;

MATCH (c:Customer)-[:HAD_INTERACTION]->(i:Interaction)
WITH c, i ORDER BY i.occurred_at, i.interaction_id
WITH c, collect(i) AS seq
UNWIND range(0, size(seq) - 2) AS idx
WITH seq[idx] AS a, seq[idx + 1] AS b
MERGE (a)-[:NEXT]->(b);
