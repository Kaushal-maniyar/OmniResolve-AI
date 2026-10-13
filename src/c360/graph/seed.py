import sys
from pathlib import Path
from c360.config import settings
from c360.core.data import validate_datasets, read_csv

CYPHER_DIR = Path(__file__).resolve().parent.parent.parent.parent / "cypher"

def execute_cypher_script(session, script_path: Path, params: dict = None):
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    statements = [stmt.strip() for stmt in content.split(";") if stmt.strip()]
    for stmt in statements:
        session.run(stmt, parameters=params or {})

def purge_database(session):
    print("Purging existing database nodes, relationships, constraints, and indexes...")
    # Delete all nodes
    session.run("MATCH (n) CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 1000 ROWS")
    
    # Drop obsolete constraints
    constraints = session.run("SHOW CONSTRAINTS YIELD name").data()
    for c in constraints:
        session.run(f"DROP CONSTRAINT `{c['name']}` IF EXISTS")
        
    # Drop obsolete custom indexes
    indexes = session.run("SHOW INDEXES YIELD name, type WHERE type = 'RANGE' RETURN name").data()
    for idx in indexes:
        session.run(f"DROP INDEX `{idx['name']}` IF EXISTS")
    print("Database purge complete.")

def seed_database():
    print("--- 1. Running pre-load CSV validation ---")
    validate_datasets()

    driver = settings.get_driver()
    try:
        with driver.session(database=settings.database) as session:
            print("--- 2. Purging Existing Database Graph & Schema ---")
            purge_database(session)

            print("--- 3. Applying New Handwritten Schema Constraints & Indexes ---")
            execute_cypher_script(session, CYPHER_DIR / "01_schema.cypher")

            print("--- 4. Loading Node Entities ---")
            customers = read_csv("customers.csv")
            products = read_csv("products.csv")
            agents = read_csv("agents.csv")
            complaints = read_csv("complaints.csv")
            tickets = read_csv("tickets.csv")
            messages = read_csv("messages.csv")
            emails = read_csv("emails.csv")
            images = read_csv("images.csv")
            videos = read_csv("videos.csv")

            execute_cypher_script(
                session,
                CYPHER_DIR / "load" / "01_nodes.cypher",
                {
                    "customers": customers,
                    "products": products,
                    "agents": agents,
                    "complaints": complaints,
                    "tickets": tickets,
                    "messages": messages,
                    "emails": emails,
                    "images": images,
                    "videos": videos,
                }
            )

            print("--- 5. Loading Relationships ---")
            owns = read_csv("owns.csv")
            sent_messages = read_csv("sent_messages.csv")
            sent_emails = read_csv("sent_emails.csv")
            last_interaction = read_csv("last_interaction.csv")
            agent_sent = read_csv("agent_sent.csv")
            raises = read_csv("raises.csv")
            complaint_yes = read_csv("complaint_yes.csv")
            message_chain = read_csv("message_chain.csv")
            message_to_email = read_csv("message_to_email.csv")
            has_attachments = read_csv("has_attachments.csv")
            associated_tickets = read_csv("associated_tickets.csv")
            ticket_complaint = read_csv("ticket_complaint.csv")

            msg_images = [att for att in has_attachments if att["source_type"] == "Message" and att["attachment_type"] == "Image"]
            email_videos = [att for att in has_attachments if att["source_type"] == "Email" and att["attachment_type"] == "Video"]

            execute_cypher_script(
                session,
                CYPHER_DIR / "load" / "02_relationships.cypher",
                {
                    "owns": owns,
                    "sent_messages": sent_messages,
                    "sent_emails": sent_emails,
                    "last_interaction": last_interaction,
                    "agent_sent": agent_sent,
                    "raises": raises,
                    "complaint_yes": complaint_yes,
                    "message_chain": message_chain,
                    "message_to_email": message_to_email,
                    "msg_images": msg_images,
                    "email_videos": email_videos,
                    "associated_tickets": associated_tickets,
                    "ticket_complaints": ticket_complaint,
                }
            )

            print("--- 6. Schema seeding complete! ---")
    finally:
        driver.close()

    # Import and run verification
    from c360.graph.verify import verify_database
    success = verify_database()
    if not success:
        print("VERIFICATION FAILED AFTER SEEDING!")
        sys.exit(1)
    print("New schema seeding and verification completed successfully!")

if __name__ == "__main__":
    seed_database()
