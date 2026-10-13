// OWNS
UNWIND $owns AS row
MATCH (c:Customer {id: row.customer_id})
MATCH (p:Product  {id: row.product_id})
MERGE (c)-[r:OWNS]->(p)
SET r.date = datetime(row.date);

// SENT (Customer -> Message)
UNWIND $sent_messages AS row
MATCH (c:Customer {id: row.customer_id})
MATCH (m:Message  {id: row.message_id})
MERGE (c)-[:SENT]->(m);

// SENT (Customer -> Email)
UNWIND $sent_emails AS row
MATCH (c:Customer {id: row.customer_id})
MATCH (e:Email    {id: row.email_id})
MERGE (c)-[:SENT]->(e);

// LAST_INTERACTION (Customer -> Email)
UNWIND $last_interaction AS row
MATCH (c:Customer {id: row.customer_id})
MATCH (e:Email    {id: row.email_id})
MERGE (c)-[:LAST_INTERACTION]->(e);

// SENT (Agent -> Message)
UNWIND $agent_sent AS row
MATCH (a:Agent   {id: row.agent_id})
MATCH (m:Message {id: row.message_id})
MERGE (a)-[:SENT]->(m);

// RAISE (Agent -> Ticket)
UNWIND $raises AS row
MATCH (a:Agent  {id: row.agent_id})
MATCH (t:Ticket {id: row.ticket_id})
MERGE (a)-[r:RAISE]->(t)
SET r.date = datetime(row.date);

// YES (Complaint -> Message)
UNWIND $complaint_yes AS row
MATCH (cmp:Complaint {id: row.complaint_id})
MATCH (m:Message     {id: row.message_id})
MERGE (cmp)-[:YES]->(m);

// NEXT & PRE (Message -> Message)
UNWIND $message_chain AS row
MATCH (m1:Message {id: row.prev_message_id})
MATCH (m2:Message {id: row.next_message_id})
MERGE (m1)-[:NEXT]->(m2)
MERGE (m2)-[:PRE]->(m1);

// NEXT & PRE (Message -> Email)
UNWIND $message_to_email AS row
MATCH (m:Message {id: row.message_id})
MATCH (e:Email   {id: row.email_id})
MERGE (m)-[:NEXT]->(e)
MERGE (e)-[:PRE]->(m);

// HAS (Message -> Image)
UNWIND $msg_images AS row
MATCH (m:Message {id: row.source_id})
MATCH (img:Image {id: row.attachment_id})
MERGE (m)-[:HAS]->(img);

// HAS (Email -> Video)
UNWIND $email_videos AS row
MATCH (e:Email   {id: row.source_id})
MATCH (v:Video   {id: row.attachment_id})
MERGE (e)-[:HAS]->(v);

// ASSOCIATED (Message -> Ticket)
UNWIND $associated_tickets AS row
MATCH (m:Message {id: row.message_id})
MATCH (t:Ticket  {id: row.ticket_id})
MERGE (m)-[:ASSOCIATED]->(t);

// ASSOCIATED (Ticket -> Complaint)
UNWIND $ticket_complaints AS row
MATCH (t:Ticket      {id: row.ticket_id})
MATCH (cmp:Complaint {id: row.complaint_id})
MERGE (t)-[:ASSOCIATED]->(cmp);
