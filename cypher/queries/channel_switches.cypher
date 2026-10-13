MATCH (c:Customer)-[:HAD_INTERACTION]->(i1:Interaction)-[:NEXT]->(i2:Interaction),
      (i1)-[:VIA]->(ch1:Channel), (i2)-[:VIA]->(ch2:Channel)
WHERE ch1 <> ch2
RETURN c.customer_id AS customer_id, c.name AS customer,
       ch1.name AS previous_channel, ch2.name AS next_channel,
       i1.occurred_at AS previous_time, i2.occurred_at AS next_time
ORDER BY c.customer_id, i1.occurred_at;
