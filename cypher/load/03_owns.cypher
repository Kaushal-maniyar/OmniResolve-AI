UNWIND $rows AS row
MATCH (c:Customer {customer_id: row.customer_id})
MATCH (p:Product  {product_id:  row.product_id})
MERGE (c)-[:OWNS]->(p);
