# Neo4j Graph Model — Handwritten Schema Specification

## Diagram & Entity Relationships

```text
                     (Customer)
        ┌────────────────┼────────────────┐
      OWNS             SENT        LAST_INTERACTION
        │                │                │
        ▼                ▼                ▼
    (Product)        (Message) ──NEXT──► (Email)
                         │    ◄──PRE───      │
                        HAS                 HAS
                         │                   │
                         ▼                   ▼
                      (Image)             (Video)

   (Complaint) ──YES──► (Message) ──ASSOCIATED──► (Ticket)
                                                     ▲
   (Agent) ──RAISE──► (Ticket) ──ASSOCIATED──► (Complaint)
   (Agent) ──SENT───► (Message)
```

## Graph Summary & Invariants

- **Node Types (9)**:
  - `Customer`: `id`, `name`, `email`
  - `Product`: `id`, `name`
  - `Agent`: `id`, `name`, `type` (`"Human"` | `"LLM"`)
  - `Complaint`: `id`, `status`
  - `Ticket`: `id`, `status`, `problem_des`
  - `Message`: `id`, `date` (DATETIME), `content`
  - `Email`: `id`, `date` (DATETIME), `sub`, `body`
  - `Image`: `id`, `path`
  - `Video`: `id`, `path`

- **Relationships (9 Types, 14 Directional Rules)**:
  - `(Customer)-[:OWNS {date: DATETIME}]->(Product)`
  - `(Customer)-[:SENT]->(Message)`
  - `(Customer)-[:SENT]->(Email)`
  - `(Customer)-[:LAST_INTERACTION]->(Email)`
  - `(Agent)-[:SENT]->(Message)`
  - `(Agent)-[:RAISE {date: DATETIME}]->(Ticket)`
  - `(Complaint)-[:YES]->(Message)`
  - `(Message)-[:NEXT]->(Message)` / `(Message)-[:PRE]->(Message)`
  - `(Message)-[:NEXT]->(Email)` / `(Email)-[:PRE]->(Message)`
  - `(Message)-[:HAS]->(Image)`
  - `(Email)-[:HAS]->(Video)`
  - `(Message)-[:ASSOCIATED]->(Ticket)`
  - `(Ticket)-[:ASSOCIATED]->(Complaint)`
