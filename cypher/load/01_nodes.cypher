UNWIND $customers AS row
MERGE (c:Customer {id: row.id})
SET c.name = row.name, c.email = row.email;

UNWIND $products AS row
MERGE (p:Product {id: row.id})
SET p.name = row.name;

UNWIND $agents AS row
MERGE (a:Agent {id: row.id})
SET a.name = row.name, a.type = row.type;

UNWIND $complaints AS row
MERGE (cmp:Complaint {id: row.id})
SET cmp.status = row.status;

UNWIND $tickets AS row
MERGE (t:Ticket {id: row.id})
SET t.status = row.status, t.problem_des = row.problem_des;

UNWIND $messages AS row
MERGE (m:Message {id: row.id})
SET m.date = datetime(row.date), m.content = row.content;

UNWIND $emails AS row
MERGE (e:Email {id: row.id})
SET e.date = datetime(row.date), e.sub = row.sub, e.body = row.body;

UNWIND $images AS row
MERGE (img:Image {id: row.id})
SET img.path = row.path;

UNWIND $videos AS row
MERGE (v:Video {id: row.id})
SET v.path = row.path;
