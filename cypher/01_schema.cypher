CREATE CONSTRAINT customer_id_unique   IF NOT EXISTS FOR (n:Customer)  REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT product_id_unique    IF NOT EXISTS FOR (n:Product)   REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT message_id_unique    IF NOT EXISTS FOR (n:Message)   REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT complaint_id_unique  IF NOT EXISTS FOR (n:Complaint) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT email_id_unique      IF NOT EXISTS FOR (n:Email)     REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT image_id_unique      IF NOT EXISTS FOR (n:Image)     REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT video_id_unique      IF NOT EXISTS FOR (n:Video)     REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT agent_id_unique      IF NOT EXISTS FOR (n:Agent)     REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT ticket_id_unique     IF NOT EXISTS FOR (n:Ticket)    REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT customer_phone_unique IF NOT EXISTS FOR (n:Customer) REQUIRE n.phone IS UNIQUE;

CREATE INDEX customer_email IF NOT EXISTS FOR (n:Customer) ON (n.email);
CREATE INDEX message_date   IF NOT EXISTS FOR (n:Message)  ON (n.date);
CREATE INDEX ticket_status  IF NOT EXISTS FOR (n:Ticket)   ON (n.status);
