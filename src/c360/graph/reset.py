import sys
from c360.config import settings

def reset_demo_data():
    print("Resetting Customer 360 demo graph data...")
    driver = settings.get_driver()
    try:
        with driver.session(database=settings.database) as session:
            cypher = """
            MATCH (n) WHERE n:Customer OR n:Interaction OR n:Ticket OR n:Agent OR n:Channel OR n:Product
            CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 1000 ROWS
            """
            session.run(cypher)
            print("Demo data reset completed successfully (schema, constraints & indexes preserved).")
    finally:
        driver.close()

if __name__ == "__main__":
    reset_demo_data()
