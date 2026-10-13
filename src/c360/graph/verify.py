import sys
from c360.config import settings

def run_check(session, name: str, query: str, expected) -> bool:
    result = session.run(query).single()
    actual = result[0] if result else None
    passed = actual == expected
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}: expected={expected}, actual={actual}")
    return passed

def verify_database() -> bool:
    print("=== STARTING GRAPH INVARIANT VERIFICATION SUITE (NEW HANDWRITTEN SCHEMA) ===")
    driver = settings.get_driver()
    all_passed = True

    try:
        with driver.session(database=settings.database) as session:
            # 1. Constraints Check
            all_passed &= run_check(
                session, "Schema: Uniqueness Constraints Count",
                "SHOW CONSTRAINTS YIELD type WHERE type = 'UNIQUENESS' RETURN count(*)",
                9
            )

            # 2. Performance Indexes Check
            all_passed &= run_check(
                session, "Schema: Performance Indexes Count",
                "SHOW INDEXES YIELD name, type WHERE type = 'RANGE' AND name IN ['customer_email', 'message_date', 'ticket_status'] RETURN count(*)",
                3
            )

            # 3. Node Label Counts
            node_counts = {
                "Customer": 5, "Product": 5, "Agent": 4, "Complaint": 3,
                "Ticket": 3, "Message": 4, "Email": 2, "Image": 2, "Video": 2
            }
            for label, count in node_counts.items():
                all_passed &= run_check(
                    session, f"Node Count: {label}",
                    f"MATCH (n:{label}) RETURN count(n)",
                    count
                )

            # 4. Total Nodes Count
            all_passed &= run_check(
                session, "Total Node Count",
                "MATCH (n) RETURN count(n)",
                30
            )

            # 5. Relationship Counts
            rel_counts = {
                "OWNS": 5, "SENT": 6, "LAST_INTERACTION": 2, "RAISE": 3,
                "YES": 2, "NEXT": 3, "PRE": 3, "HAS": 4, "ASSOCIATED": 4
            }
            for rel_type, count in rel_counts.items():
                all_passed &= run_check(
                    session, f"Relationship Count: {rel_type}",
                    f"MATCH ()-[r:{rel_type}]->() RETURN count(r)",
                    count
                )

            all_passed &= run_check(
                session, "Total Relationship Count",
                "MATCH ()-[r]->() RETURN count(r)",
                32
            )

            # 6. Bi-directional Symmetry: (a)-[:NEXT]->(b) <=> (b)-[:PRE]->(a)
            all_passed &= run_check(
                session, "Chain Symmetry: Every NEXT has matching reverse PRE",
                "MATCH (a)-[:NEXT]->(b) WHERE NOT (b)-[:PRE]->(a) RETURN count(*)",
                0
            )

            # 7. Obsolete Elements Purge Check
            all_passed &= run_check(
                session, "Purge Verification: Zero obsolete Interaction/Channel nodes exist",
                "MATCH (n) WHERE n:Interaction OR n:Channel RETURN count(n)",
                0
            )

            # 8. Smoke Query Check for C001
            smoke_cypher = """
            MATCH (c:Customer {id: 'C001'})
            RETURN
              COUNT { (c)-[:OWNS]->() } AS num_owns,
              COUNT { (c)-[:SENT]->() } AS num_sent,
              COUNT { (c)-[:LAST_INTERACTION]->() } AS num_last_int
            """
            smoke_res = session.run(smoke_cypher).single()
            smoke_valid = (smoke_res["num_owns"] == 2 and smoke_res["num_sent"] == 3 and smoke_res["num_last_int"] == 1)
            all_passed &= smoke_valid
            status = "PASS" if smoke_valid else "FAIL"
            print(f"[{status}] Smoke Test C001: 2 owns, 3 sent, 1 last_interaction -> {dict(smoke_res)}")

    finally:
        driver.close()

    print(f"=== VERIFICATION SUMMARY: {'ALL PASSED' if all_passed else 'SOME CHECKS FAILED'} ===")
    return all_passed

if __name__ == "__main__":
    success = verify_database()
    sys.exit(0 if success else 1)
