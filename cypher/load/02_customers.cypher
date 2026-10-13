UNWIND $rows AS row
MERGE (c:Customer {customer_id: row.customer_id})
SET c.name = row.name, c.email = row.email, c.phone = row.phone,
    c.segment = row.segment, c.location = row.location,
    c.created_at = datetime(row.created_at);
