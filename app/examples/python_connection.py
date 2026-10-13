import sys
from pathlib import Path

# Add src to python path for standalone execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from neo4j import GraphDatabase
from c360.config import settings

QUERY = """
MATCH (c:Customer)
OPTIONAL MATCH (c)-[:SENT]->(m:Message)
OPTIONAL MATCH (c)-[:SENT]->(e:Email)
RETURN c.id AS id, c.name AS name, c.email AS email,
       count(m) AS sent_messages, count(e) AS sent_emails
ORDER BY c.id
"""

def main():
    print(f"Connecting to Neo4j at {settings.uri}...")
    with GraphDatabase.driver(settings.uri, auth=(settings.username, settings.password)) as driver:
        driver.verify_connectivity()
        print("Bolt connectivity verified!")
        records, _, _ = driver.execute_query(QUERY, database_=settings.database)
        print("\nCustomers in Updated Handwritten Neo4j Graph:")
        for r in records:
            print(f"  {r['id']}: {r['name']} ({r['email']}) -> Messages: {r['sent_messages']}, Emails: {r['sent_emails']}")

if __name__ == "__main__":
    main()
