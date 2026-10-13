# Neo4j Customer 360 — Optimised Implementation Plan (v2)

> **Target:** locally hosted Neo4j Community Edition on Windows, running as a Windows service, no Docker.
> **Consumer:** Antigravity (agentic implementer) and any human developer reproducing the setup.
> **Supersedes:** `neo4j_customer360_antigravity_implementation_plan.md` (v1).

---

## 0. Review of v1 — what was wrong and what changed

| # | Finding in v1 | Severity | Resolution in v2 |
|---|---|---|---|
| F1 | Windows paths and commands were corrupted by escape sequences (`C:\neo4j\...` split across lines, `.\scripts\verify.ps1` broken). An agent copying them literally would fail. | High | All paths and commands are in fenced code blocks, written verbatim (§4, §13). |
| F2 | Authentication is required, but no step ever sets the Neo4j password. `.env` is created but nothing reads it. | High | Explicit initial-password step before first start; scripts and Python read `.env` (§12, §13). |
| F3 | Two sources of truth for data (`data/*.csv` **and** `cypher/03..05_*.cypher`). They will drift. | High | CSV is the only source of truth; Cypher files are parameterised loaders (§7, §9). |
| F4 | Required data is missing: no `OWNS` rows, no mapping of ticket → originating interaction, no timestamps, no summaries, no ticket dates. An implementer must invent them, so results vary run to run. | High | Complete deterministic dataset specified (§7). |
| F5 | Neo4j version is "pinned" but never chosen, and the pin is repeated in three files. Neo4j now uses calendar versioning and the Java requirement changed. | Medium | One `neo4j.version` file is the single source; Java and Browser checks added as gates (§4). |
| F6 | Service vs "supported server process" is ambiguous (§7 vs §19 of v1). | Medium | Service is the only runtime mode. `neo4j console` is debugging only (§12). |
| F7 | `NEXT` **and** `PREVIOUS` stored. Relationships are traversable in both directions, so `PREVIOUS` doubles edges and creates a consistency risk. | Medium | `PREVIOUS` dropped; reverse traversal `<-[:NEXT]-` used. Opt-back instructions in §5.3. |
| F8 | `NEXT` links hand-written pair by pair. | Medium | Chain is derived from `occurred_at` by one idempotent query (§9.3). |
| F9 | Property named `datetime` and timestamps implied as strings. | Low/Med | Renamed `occurred_at`; all times are native `DATETIME` values (§5.2). |
| F10 | Customer 360 query chains many `OPTIONAL MATCH` clauses (row multiplication), collects channels/agents/products separately (loses which interaction used which), returns raw nodes. | Medium | `COLLECT {}` subqueries return ordered, correlated maps (§10). |
| F11 | Verification only checks counts and "relationship exists". Parsing shell output to fail is brittle. | Medium | Invariant-based verification in Python with exit codes (§11). |
| F12 | Python example reads env vars but never loads `.env`, so `PASSWORD` is `None`. Driver not closed on error. | Low/Med | `python-dotenv`, context managers, fail-fast on missing password (§13). |
| F13 | Community Edition limits not acknowledged (single user database, no RBAC, no property-existence constraints, offline-only dump). | Low/Med | Stated in §3; required-property rules enforced by verification instead of constraints. |
| F14 | `reset-demo-data` unspecified (an unbounded `DETACH DELETE` can exhaust transaction memory). | Low | Label-scoped, batched delete (§12.5). |
| F15 | No listener binding, heap sizing, admin elevation, port checks, or service startup type. | Medium | Managed config block and preflight checks (§8, §12). |
| F16 | Relationships listed four times, rules listed in three places. | Low | Consolidated; each fact appears once. |
| F17 | "Test on a clean machine" had no method. | Low | Windows Sandbox or fresh VM procedure (§15.3). |

### Decisions that deviate from v1 (confirm or revert)

1. **`PREVIOUS` removed** (F7). Revert instructions in §5.3.
2. **Python is a required runtime** for seeding and verification (F3, F11). PowerShell remains the orchestrator and service manager.
3. **`Interaction.datetime` renamed `occurred_at`** (F9).

---

## 1. Objective

Provide a reproducible, script-driven Neo4j Customer 360 graph on a Windows laptop so that:

- Neo4j runs as a **Windows service**, independent of any application, IDE or terminal.
- Any local application (FastAPI, LangGraph, Java, Node.js) connects through **Bolt** (`bolt://localhost:7687`).
- The schema, 10-customer synthetic dataset and verification suite are version-controlled; a second laptop recreates the same logical graph by following this document.

This is the local data foundation for OmniResolve AI.

---

## 2. Non-negotiable rules

1. No Docker, Kubernetes, cloud Neo4j or other extra infrastructure.
2. Neo4j is installed outside the repository (e.g. `C:\neo4j\...`). Database files are never in Git.
3. Applications connect only via Bolt and never touch database files.
4. Credentials live only in `.env` (git-ignored). No hardcoded passwords.
5. Application code uses parameterised Cypher only.
6. The database lifecycle is never controlled by the application.
7. Seeding is idempotent (`MERGE`), and re-running it changes nothing.
8. All data is synthetic.
9. Neo4j version is pinned (no "latest"), recorded in one file.
10. Never invent Neo4j commands or config keys: check `--help` and the docs for the **pinned** version before using them (service and admin commands have changed across releases).

---

## 3. Architecture

```text
Windows laptop
│
├── Neo4j Community Edition (pinned version)     ← Windows service "neo4j"
│     ├── Bolt          127.0.0.1:7687
│     └── Browser/HTTP  127.0.0.1:7474   (if shipped, see Gate G0)
│
└── customer-360-neo4j (Git repository)
      ├── data/*.csv          single source of truth for demo data
      ├── cypher/             schema, loaders, queries
      ├── src/c360/           seed + verify (Python, Bolt)
      └── scripts/*.ps1       install, service lifecycle, orchestration
```

Applications only know four values: `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`.

**Community Edition constraints the design respects**

- One user database (`neo4j`). Do not plan multi-database layouts.
- No role-based access control (single admin user for now).
- No property-existence constraints, so "required" properties are enforced by the verification suite (§11).
- Backups are offline (`neo4j-admin database dump` with the service stopped). The demo data is reproducible from Git, so no backup job is needed until real data exists.

**Data ownership**

| Layer | Owns |
|---|---|
| Neo4j | Relationships, interaction history, ticket links, customer journey |
| Application | API logic, agent orchestration, auth, conversation state |
| Future vector DB | Troubleshooting documents, embeddings, semantic search |
| Future LLM layer | Reasoning, diagnosis, response generation |

Neo4j is not a document store.

---

## 4. Prerequisites, version pinning and gates

### 4.1 Pin file

Create `neo4j.version` at repo root. This is the only place the version is written. README, docs and scripts read or reference it.

```text
NEO4J_VERSION=<exact release, e.g. 2026.07.1>
NEO4J_ZIP_SHA256=<sha256 published on the Neo4j Deployment Center>
REQUIRED_JAVA_MAJOR=<value from the system-requirements page for that release>
```

Neo4j uses calendar versioning for current releases. At the time of writing, the official Windows docs reference 2026.07.1. Choose one concrete release, download the Windows ZIP only from the official Deployment Center, and record its SHA-256. Do not guess download URLs.

### 4.2 Prerequisites

| Item | Requirement |
|---|---|
| OS | Windows 10/11, 64-bit, administrator rights for service operations |
| Java | JDK matching the system-requirements page for the pinned release. For 2025.x/2026.x docs this is Java 21 (Java 25 is also listed from 2025.10 onward). Verify before use. |
| Git | Any recent version |
| Python | 3.11+ (required: seeding and verification) |
| Install path | No spaces, e.g. `C:\neo4j\neo4j-community-<VERSION>` |

### 4.3 Gates

| Gate | Check | Pass criterion |
|---|---|---|
| **G0** | Read the pinned release's system-requirements and Windows install pages. Extract the ZIP and list `bin\`. | Java major recorded; `bin\neo4j.bat` and `bin\neo4j-admin.bat` exist; **Browser availability confirmed.** Recent docs state Community does not include graph tools such as visualisation by default, so if Browser is not bundled, record the supported alternative (e.g. Neo4j Desktop or the Query tool) in `docs/neo4j-windows-setup.md` and change the "Browser" checks to that tool. Bolt connectivity does not depend on it. |
| **G0b** | Compare ZIP hash with `NEO4J_ZIP_SHA256`. | Match |

---

## 5. Graph model (final)

### 5.1 Diagram

```text
                    (Customer)
        ┌──────────────┼───────────────┐
   HAS_TICKET    HAD_INTERACTION      OWNS
        ▼              ▼               ▼
    (Ticket)      (Interaction)    (Product)
     │    │         │  │  │  │
     │    │         │  │  │  └── NEXT ──> (Interaction)   per-customer chronological chain
     │    │         │  │  └───── ABOUT ─> (Product)
     │    │         │  └──────── HANDLED_BY ─> (Agent)
     │    │         └─────────── VIA ─> (Channel)
     │    └── ABOUT ──> (Product)
     └────── GENERATED_FROM ──> (Interaction)
```

`Interaction` is the central event node.

### 5.2 Node properties

| Node | Properties (type) |
|---|---|
| `Customer` | `customer_id` (string, unique), `name`, `email` (unique), `phone`, `segment`, `location`, `created_at` (DATETIME) |
| `Interaction` | `interaction_id` (unique), `type`, `occurred_at` (DATETIME), `subject`, `sentiment`, `summary` |
| `Ticket` | `ticket_id` (unique), `status`, `priority`, `created_at` (DATETIME), `resolved_at` (DATETIME, absent unless Resolved), `description` |
| `Agent` | `agent_id` (unique), `name`, `team` |
| `Channel` | `channel_id` (unique), `name` |
| `Product` | `product_id` (unique), `name`, `category` |

Enumerations (enforced by verification):

```text
Interaction.type      Complaint | Query | Follow-up | Troubleshooting | Escalation | Resolution
Interaction.sentiment Positive | Neutral | Negative
Ticket.status         Open | In Progress | Escalated | Resolved
Ticket.priority       Low | Medium | High | Critical
Customer.segment      Consumer | SMB | Enterprise
```

### 5.3 Relationships and cardinality

| Relationship | Cardinality rule |
|---|---|
| `(Customer)-[:HAD_INTERACTION]->(Interaction)` | each Interaction has exactly 1 Customer |
| `(Customer)-[:HAS_TICKET]->(Ticket)` | each Ticket has exactly 1 Customer |
| `(Customer)-[:OWNS]->(Product)` | many-to-many |
| `(Interaction)-[:VIA]->(Channel)` | exactly 1 |
| `(Interaction)-[:HANDLED_BY]->(Agent)` | exactly 1 |
| `(Interaction)-[:ABOUT]->(Product)` | exactly 1 |
| `(Interaction)-[:NEXT]->(Interaction)` | linear chain **per customer**, ordered by `occurred_at` (tie-break `interaction_id`) |
| `(Ticket)-[:GENERATED_FROM]->(Interaction)` | exactly 1, and the interaction belongs to the same customer |
| `(Ticket)-[:ABOUT]->(Product)` | exactly 1, equal to the source interaction's product |

`ABOUT` is used from two source labels. Always qualify by label when counting.

**Why no `PREVIOUS`:** the previous interaction is `(i)<-[:NEXT]-(prev)`. A second edge adds writes, storage and a way to become inconsistent. **To keep it anyway:** in the chain builder (§9.3) add `MERGE (b)-[:PREVIOUS]->(a)` after the `NEXT` merge, delete both types before rebuilding, and add 15 to the expected relationship counts.

**Possible later extension (not in scope):** `(Interaction)-[:RELATES_TO]->(Ticket)` to link follow-up interactions to a ticket. Today `GENERATED_FROM` only links the originating interaction.

---

## 6. Repository structure

```text
customer-360-neo4j/
├── README.md
├── .gitignore
├── .gitattributes
├── .env.example
├── neo4j.version
├── requirements.txt
│
├── config/
│   └── neo4j.overrides.conf          # merged into the install's neo4j.conf (managed block)
│
├── docs/
│   ├── neo4j-windows-setup.md
│   └── graph-model.md
│
├── data/                              # SINGLE SOURCE OF TRUTH
│   ├── agents.csv
│   ├── channels.csv
│   ├── products.csv
│   ├── customers.csv
│   ├── owns.csv
│   ├── interactions.csv
│   └── tickets.csv
│
├── cypher/
│   ├── 01_schema.cypher               # constraints + indexes
│   ├── load/
│   │   ├── 01_reference.cypher        # agents, channels, products   ($rows)
│   │   ├── 02_customers.cypher
│   │   ├── 03_owns.cypher
│   │   ├── 04_interactions.cypher
│   │   ├── 05_tickets.cypher
│   │   └── 06_chain.cypher            # derives NEXT
│   └── queries/
│       ├── customer_360.cypher
│       ├── customer_journey.cypher
│       ├── channel_switches.cypher
│       ├── ticket_history.cypher
│       └── latest_interaction.cypher
│
├── src/c360/
│   ├── config.py                      # loads .env, builds driver
│   ├── data.py                        # CSV read + pre-load validation
│   ├── seed.py                        # python -m c360.seed
│   ├── verify.py                      # python -m c360.verify (exit code 0/1)
│   └── reset.py                       # python -m c360.reset
│
├── tests/
│   └── test_data.py                   # DB-free validation of the CSVs
│
├── scripts/
│   ├── common.ps1                     # shared helpers (dot-sourced)
│   ├── install-neo4j.ps1              # hash check + extract ZIP
│   ├── setup.ps1                      # one-shot first-time setup
│   ├── start-neo4j.ps1
│   ├── stop-neo4j.ps1
│   ├── restart-neo4j.ps1
│   ├── status-neo4j.ps1
│   ├── uninstall-service.ps1
│   ├── seed.ps1
│   ├── verify.ps1
│   └── reset-demo-data.ps1
│
└── app/examples/python_connection.py
```

`.gitignore` must include:

```gitignore
.env
.venv/
__pycache__/
*.pyc
.pytest_cache/
*.dump
```

`.gitattributes` (avoids CRLF/LF diffs in data and Cypher):

```gitattributes
*.csv     text eol=lf
*.cypher  text eol=lf
*.ps1     text eol=crlf
*.md      text eol=lf
```

`.env.example`:

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=CHANGE_ME
NEO4J_DATABASE=neo4j
NEO4J_HOME=C:\neo4j\neo4j-community-<VERSION>
NEO4J_SERVICE_NAME=neo4j
```

`requirements.txt`: the `neo4j` Python driver and `python-dotenv` (and `pytest` for tests). Pin exact versions after the first successful run.

---

## 7. Dataset specification (deterministic)

Write these into `data/*.csv`. Timestamps are ISO-8601 with the IST offset (`+05:30`). Empty `resolved_at` means null.

### 7.1 Reference data

`agents.csv`

| agent_id | name | team |
|---|---|---|
| A001 | Amit Kumar | Broadband Support |
| A002 | Priya Singh | Enterprise Support |
| A003 | Rahul Shah | Network Operations |
| A004 | Sneha Patel | Technical Support |
| A005 | Vikram Rao | Escalation Team |

`channels.csv`: CH001 WhatsApp, CH002 Phone, CH003 Email, CH004 Web Chat.

`products.csv`

| product_id | name | category |
|---|---|---|
| P001 | Business Broadband | Connectivity |
| P002 | Internet Leased Line | Connectivity |
| P003 | SIP Trunk | Voice |
| P004 | Oracle SBC | Network Infrastructure |
| P005 | Enterprise WiFi | Connectivity |

### 7.2 Customers

Email is `<first>.<last>@example.com`, phone is `+91-90000000NN`. `created_at` is fixed in the CSV (never `now()`), so re-seeding is stable.

| customer_id | name | segment | location | created_at |
|---|---|---|---|---|
| C001 | Aarav Shah | Enterprise | Ahmedabad | 2023-11-10T00:00:00+05:30 |
| C002 | Riya Patel | SMB | Mumbai | 2024-01-15T00:00:00+05:30 |
| C003 | Arjun Mehta | Enterprise | Bengaluru | 2023-08-22T00:00:00+05:30 |
| C004 | Neha Desai | SMB | Pune | 2024-02-05T00:00:00+05:30 |
| C005 | Karan Joshi | Enterprise | Delhi | 2023-06-30T00:00:00+05:30 |
| C006 | Meera Shah | Consumer | Ahmedabad | 2024-04-18T00:00:00+05:30 |
| C007 | Rahul Verma | SMB | Hyderabad | 2024-05-09T00:00:00+05:30 |
| C008 | Priya Nair | Enterprise | Chennai | 2023-09-12T00:00:00+05:30 |
| C009 | Aditya Rao | Consumer | Bengaluru | 2024-06-25T00:00:00+05:30 |
| C010 | Simran Kapoor | Enterprise | Mumbai | 2023-12-01T00:00:00+05:30 |

Phones are `+91-9000000001` through `+91-9000000010` in ID order, as in v1.

### 7.3 Ownership (`owns.csv`, 15 rows)

Rule: a customer must own every product they raised an interaction about (checked in §11). Five customers own one extra product so the graph is not a trivial 1:1.

```text
C001: P001, P005     C002: P002           C003: P003, P001
C004: P001           C005: P004, P002     C006: P005
C007: P001           C008: P003, P002     C009: P005
C010: P002, P003
```

### 7.4 Interactions (`interactions.csv`, 25 rows)

Columns: `interaction_id, customer_id, channel_id, agent_id, product_id, type, occurred_at, subject, sentiment, summary`.
`summary` is one factual sentence consistent with `subject` and `type` (written once, then committed, never regenerated).

| id | cust | channel | agent | prod | type | occurred_at | subject | sentiment |
|---|---|---|---|---|---|---|---|---|
| I001 | C001 | CH001 | A001 | P001 | Complaint | 2026-09-01T09:15 | Intermittent broadband connectivity | Negative |
| I002 | C001 | CH002 | A003 | P001 | Troubleshooting | 2026-09-02T11:30 | Line diagnostics and signal check | Neutral |
| I003 | C001 | CH003 | A002 | P001 | Resolution | 2026-09-03T15:45 | Fault fixed, service stable | Positive |
| I004 | C002 | CH001 | A001 | P002 | Complaint | 2026-09-05T10:00 | High packet loss on leased line | Negative |
| I005 | C002 | CH004 | A004 | P002 | Follow-up | 2026-09-07T14:20 | Packet loss persists, asking for update | Negative |
| I006 | C003 | CH002 | A003 | P003 | Complaint | 2026-09-08T08:40 | SIP call quality degradation | Negative |
| I007 | C003 | CH003 | A002 | P003 | Troubleshooting | 2026-09-08T13:10 | Codec and jitter analysis | Neutral |
| I008 | C003 | CH002 | A005 | P003 | Resolution | 2026-09-09T10:25 | Trunk reconfigured, quality restored | Positive |
| I009 | C004 | CH001 | A001 | P001 | Complaint | 2026-09-10T16:05 | Intermittent broadband connectivity | Negative |
| I010 | C004 | CH004 | A004 | P001 | Troubleshooting | 2026-09-12T11:15 | Router reset and line test | Neutral |
| I011 | C005 | CH003 | A002 | P004 | Complaint | 2026-09-11T09:30 | Oracle SBC registration failure | Negative |
| I012 | C005 | CH002 | A003 | P004 | Resolution | 2026-09-12T17:00 | Registration restored after config fix | Positive |
| I013 | C006 | CH004 | A004 | P005 | Query | 2026-09-14T12:00 | Enterprise WiFi authentication problem | Neutral |
| I014 | C006 | CH001 | A001 | P005 | Follow-up | 2026-09-16T10:10 | Still unable to authenticate | Neutral |
| I015 | C007 | CH001 | A001 | P001 | Complaint | 2026-09-15T18:20 | Intermittent broadband connectivity | Negative |
| I016 | C007 | CH002 | A003 | P001 | Resolution | 2026-09-16T12:35 | Line fault cleared | Positive |
| I017 | C008 | CH001 | A002 | P003 | Complaint | 2026-09-17T09:05 | SIP call quality degradation | Negative |
| I018 | C008 | CH002 | A005 | P003 | Escalation | 2026-09-17T14:50 | Escalated to escalation team | Negative |
| I019 | C008 | CH003 | A002 | P003 | Follow-up | 2026-09-18T11:40 | Awaiting escalation outcome | Negative |
| I020 | C009 | CH004 | A004 | P005 | Query | 2026-09-19T13:25 | Enterprise WiFi authentication problem | Neutral |
| I021 | C009 | CH001 | A001 | P005 | Resolution | 2026-09-20T10:50 | Credentials re-provisioned | Positive |
| I022 | C010 | CH001 | A002 | P002 | Complaint | 2026-09-21T09:45 | High packet loss on leased line | Negative |
| I023 | C010 | CH002 | A003 | P002 | Troubleshooting | 2026-09-22T15:30 | Link utilisation and path trace | Neutral |
| I024 | C010 | CH003 | A002 | P002 | Follow-up | 2026-09-23T11:05 | Packet loss continues | Negative |
| I025 | C010 | CH002 | A005 | P002 | Escalation | 2026-09-24T16:40 | Escalated for carrier-side investigation | Negative |

(Append `:00+05:30` to every time in the CSV.)

### 7.5 Tickets (`tickets.csv`, 10 rows)

Columns: `ticket_id, customer_id, source_interaction_id, product_id, status, priority, created_at, resolved_at, description`.

Rules: `created_at` = the source interaction's `occurred_at`. For Resolved tickets `resolved_at` = `occurred_at` of that customer's `Resolution` interaction. All other statuses have empty `resolved_at`.

| ticket | cust | source | prod | status | priority | created_at | resolved_at | description |
|---|---|---|---|---|---|---|---|---|
| T001 | C001 | I001 | P001 | Resolved | High | 2026-09-01T09:15 | 2026-09-03T15:45 | Intermittent broadband connectivity |
| T002 | C002 | I004 | P002 | Open | Medium | 2026-09-05T10:00 | | High packet loss on leased line |
| T003 | C003 | I006 | P003 | Resolved | Critical | 2026-09-08T08:40 | 2026-09-09T10:25 | SIP call quality degradation |
| T004 | C004 | I009 | P001 | In Progress | Medium | 2026-09-10T16:05 | | Intermittent broadband connectivity |
| T005 | C005 | I011 | P004 | Resolved | High | 2026-09-11T09:30 | 2026-09-12T17:00 | Oracle SBC registration failure |
| T006 | C006 | I013 | P005 | Open | Low | 2026-09-14T12:00 | | Enterprise WiFi authentication problem |
| T007 | C007 | I015 | P001 | Resolved | Medium | 2026-09-15T18:20 | 2026-09-16T12:35 | Intermittent broadband connectivity |
| T008 | C008 | I017 | P003 | Escalated | Critical | 2026-09-17T09:05 | | SIP call quality degradation |
| T009 | C009 | I020 | P005 | Resolved | Low | 2026-09-19T13:25 | 2026-09-20T10:50 | Enterprise WiFi authentication problem |
| T010 | C010 | I022 | P002 | In Progress | High | 2026-09-21T09:45 | | High packet loss on leased line |

### 7.6 Expected totals (fingerprint)

```text
Nodes:          59   (Customer 10, Agent 5, Channel 4, Product 5, Ticket 10, Interaction 25)
Relationships: 160   HAD_INTERACTION 25, VIA 25, HANDLED_BY 25, ABOUT(Interaction) 25,
                     HAS_TICKET 10, GENERATED_FROM 10, ABOUT(Ticket) 10, OWNS 15, NEXT 15
```

`NEXT` = interactions − customers = 25 − 10 = 15 (per-customer chain lengths 3,2,3,2,2,2,2,3,2,4).

---

## 8. Neo4j configuration

Do not replace the distribution's `neo4j.conf` (it is version-specific). `setup.ps1` appends a **managed block** from `config/neo4j.overrides.conf`, between markers so it is replaceable on re-run:

```properties
# >>> customer-360 managed block (do not edit by hand) >>>
server.default_listen_address=127.0.0.1
server.bolt.listen_address=127.0.0.1:7687
server.http.listen_address=127.0.0.1:7474
server.https.enabled=false
dbms.security.auth_enabled=true
server.memory.heap.initial_size=512m
server.memory.heap.max_size=1g
server.memory.pagecache.size=256m
# <<< customer-360 managed block <<<
```

Notes:

- Key names above are for current (5.x and calendar-versioned) releases. Verify each against the pinned release's configuration reference at Gate G0; remove any that the release rejects.
- Heap and page cache are deliberately small (59 nodes). Raise them only with real data (`neo4j-admin server memory-recommendation` gives guidance).
- The service stores Java options at install time. After changing Java path or JVM options, run the service `update` command and restart.
- Binding to `127.0.0.1` keeps Bolt and HTTP off the network. Remote access later requires explicit firewall, TLS and bind changes.

---

## 9. Schema and loading

### 9.1 Schema (`cypher/01_schema.cypher`)

```cypher
CREATE CONSTRAINT customer_id_unique    IF NOT EXISTS FOR (n:Customer)    REQUIRE n.customer_id    IS UNIQUE;
CREATE CONSTRAINT customer_email_unique IF NOT EXISTS FOR (n:Customer)    REQUIRE n.email          IS UNIQUE;
CREATE CONSTRAINT interaction_id_unique IF NOT EXISTS FOR (n:Interaction) REQUIRE n.interaction_id IS UNIQUE;
CREATE CONSTRAINT ticket_id_unique      IF NOT EXISTS FOR (n:Ticket)      REQUIRE n.ticket_id      IS UNIQUE;
CREATE CONSTRAINT agent_id_unique       IF NOT EXISTS FOR (n:Agent)       REQUIRE n.agent_id       IS UNIQUE;
CREATE CONSTRAINT channel_id_unique     IF NOT EXISTS FOR (n:Channel)     REQUIRE n.channel_id     IS UNIQUE;
CREATE CONSTRAINT product_id_unique     IF NOT EXISTS FOR (n:Product)     REQUIRE n.product_id     IS UNIQUE;

CREATE INDEX customer_phone         IF NOT EXISTS FOR (n:Customer)    ON (n.phone);        // WhatsApp lookup by number
CREATE INDEX interaction_occurred   IF NOT EXISTS FOR (n:Interaction) ON (n.occurred_at);
CREATE INDEX ticket_status          IF NOT EXISTS FOR (n:Ticket)      ON (n.status);
```

### 9.2 Loader mechanics

`python -m c360.seed` performs, in order:

1. **Pre-load validation of the CSVs** (`data.py`, also run by `pytest`): unique IDs, every foreign key resolves, enums valid, ticket/interaction consistency rules from §7.5 and §11. Fail before touching the database. (Needed because `MATCH` inside `UNWIND` silently drops rows with a missing target.)
2. Apply `01_schema.cypher` (split on `;`, run statement by statement).
3. Run each `cypher/load/*.cypher` with `$rows` = the parsed CSV rows (empty strings converted to `None`), in a single write transaction per file. Loaders only use `MERGE` on the key, then `SET` the remaining properties.
4. Run `06_chain.cypher`.
5. Run the verification suite and exit non-zero on failure.

Example loaders:

```cypher
// 02_customers.cypher
UNWIND $rows AS row
MERGE (c:Customer {customer_id: row.customer_id})
SET c.name = row.name, c.email = row.email, c.phone = row.phone,
    c.segment = row.segment, c.location = row.location,
    c.created_at = datetime(row.created_at);

// 04_interactions.cypher
UNWIND $rows AS row
MATCH (c:Customer    {customer_id: row.customer_id})
MATCH (ch:Channel    {channel_id:  row.channel_id})
MATCH (a:Agent       {agent_id:    row.agent_id})
MATCH (p:Product     {product_id:  row.product_id})
MERGE (i:Interaction {interaction_id: row.interaction_id})
SET i.type = row.type, i.occurred_at = datetime(row.occurred_at),
    i.subject = row.subject, i.sentiment = row.sentiment, i.summary = row.summary
MERGE (c)-[:HAD_INTERACTION]->(i)
MERGE (i)-[:VIA]->(ch)
MERGE (i)-[:HANDLED_BY]->(a)
MERGE (i)-[:ABOUT]->(p);

// 05_tickets.cypher
UNWIND $rows AS row
MATCH (c:Customer    {customer_id: row.customer_id})
MATCH (p:Product     {product_id:  row.product_id})
MATCH (i:Interaction {interaction_id: row.source_interaction_id})
MERGE (t:Ticket {ticket_id: row.ticket_id})
SET t.status = row.status, t.priority = row.priority,
    t.created_at  = datetime(row.created_at),
    t.resolved_at = CASE WHEN row.resolved_at IS NULL THEN null ELSE datetime(row.resolved_at) END,
    t.description = row.description
MERGE (c)-[:HAS_TICKET]->(t)
MERGE (t)-[:GENERATED_FROM]->(i)
MERGE (t)-[:ABOUT]->(p);
```

`01_reference.cypher` and `03_owns.cypher` follow the same pattern (`03_owns` is `MATCH` customer, `MATCH` product, `MERGE (c)-[:OWNS]->(p)`).

### 9.3 Chronology builder (`06_chain.cypher`)

The chain is a pure function of `occurred_at`, so it is rebuilt each run and cannot drift.

```cypher
MATCH ()-[n:NEXT]->() DELETE n;

MATCH (c:Customer)-[:HAD_INTERACTION]->(i:Interaction)
WITH c, i ORDER BY i.occurred_at, i.interaction_id
WITH c, collect(i) AS seq
UNWIND range(0, size(seq) - 2) AS idx          // empty range when a customer has 1 interaction
WITH seq[idx] AS a, seq[idx + 1] AS b
MERGE (a)-[:NEXT]->(b);
```

Run the delete and the build in the same transaction.

---

## 10. Queries (`cypher/queries/`)

All use parameters; none are string-built in application code. Requires 5.6+ (`COLLECT {}` subqueries), satisfied by the pinned release.

**customer_360.cypher** — one row, ordered, with interaction fields kept together:

```cypher
MATCH (c:Customer {customer_id: $customer_id})
RETURN
  c{.customer_id, .name, .email, .phone, .segment, .location, .created_at} AS customer,
  COLLECT { MATCH (c)-[:OWNS]->(p:Product) RETURN p.name ORDER BY p.name } AS owned_products,
  COLLECT {
    MATCH (c)-[:HAS_TICKET]->(t:Ticket)-[:ABOUT]->(p:Product)
    RETURN t{.ticket_id, .status, .priority, .created_at, .resolved_at, .description, product: p.name}
    ORDER BY t.created_at
  } AS tickets,
  COLLECT {
    MATCH (c)-[:HAD_INTERACTION]->(i:Interaction)-[:VIA]->(ch:Channel)
    MATCH (i)-[:HANDLED_BY]->(a:Agent)
    MATCH (i)-[:ABOUT]->(p:Product)
    RETURN i{.interaction_id, .occurred_at, .type, .subject, .sentiment, .summary,
             channel: ch.name, agent: a.name, product: p.name}
    ORDER BY i.occurred_at
  } AS interactions;
```

**customer_journey.cypher**

```cypher
MATCH (c:Customer {customer_id: $customer_id})-[:HAD_INTERACTION]->(i:Interaction),
      (i)-[:VIA]->(ch:Channel), (i)-[:HANDLED_BY]->(a:Agent), (i)-[:ABOUT]->(p:Product)
RETURN i.interaction_id, i.occurred_at, i.type, i.subject, i.sentiment, i.summary,
       ch.name AS channel, a.name AS agent, p.name AS product
ORDER BY i.occurred_at;
```

**channel_switches.cypher**

```cypher
MATCH (c:Customer)-[:HAD_INTERACTION]->(i1:Interaction)-[:NEXT]->(i2:Interaction),
      (i1)-[:VIA]->(ch1:Channel), (i2)-[:VIA]->(ch2:Channel)
WHERE ch1 <> ch2
RETURN c.customer_id AS customer_id, c.name AS customer,
       ch1.name AS previous_channel, ch2.name AS next_channel,
       i1.occurred_at AS previous_time, i2.occurred_at AS next_time
ORDER BY c.customer_id, i1.occurred_at;
```

**ticket_history.cypher**

```cypher
MATCH (c:Customer {customer_id: $customer_id})-[:HAS_TICKET]->(t:Ticket)-[:ABOUT]->(p:Product)
MATCH (t)-[:GENERATED_FROM]->(i:Interaction)
RETURN t.ticket_id, t.status, t.priority, t.created_at, t.resolved_at,
       p.name AS product, i.interaction_id AS source_interaction, i.subject AS originating_subject
ORDER BY t.created_at;
```

**latest_interaction.cypher** — chain tail plus what immediately preceded it (the "what happened just before" question for OmniResolve):

```cypher
MATCH (c:Customer {customer_id: $customer_id})-[:HAD_INTERACTION]->(last:Interaction)
WHERE NOT (last)-[:NEXT]->()
OPTIONAL MATCH (prev:Interaction)-[:NEXT]->(last)
RETURN last{.interaction_id, .occurred_at, .type, .subject, .sentiment} AS latest,
       prev{.interaction_id, .occurred_at, .type, .subject, .sentiment} AS previous;
```

---

## 11. Verification (`python -m c360.verify`)

Exit code 0 only if **every** check passes; print a PASS/FAIL line per check. `verify.ps1` wraps it and propagates the exit code.

| Group | Check | Expected |
|---|---|---|
| Schema | `SHOW CONSTRAINTS` contains the 7 uniqueness constraints; `SHOW INDEXES` contains the 3 indexes | present |
| Counts | Node counts by label (§7.6) | 10 / 5 / 4 / 5 / 10 / 25 |
| Counts | Relationship counts, label-qualified (§7.6), total 160 | exact |
| Cardinality | Interactions without exactly one each of `HAD_INTERACTION` (incoming), `VIA`, `HANDLED_BY`, `ABOUT` | 0 violators |
| Cardinality | Tickets without exactly one each of `HAS_TICKET` (incoming), `GENERATED_FROM`, `ABOUT` | 0 violators |
| Chain | Per customer: exactly 1 head and 1 tail; `NEXT` edges = interactions − 1 | all customers |
| Chain | No node with more than 1 outgoing or incoming `NEXT` | 0 |
| Chain | `NEXT` never crosses customers; `a.occurred_at < b.occurred_at` for every `NEXT` | 0 violators |
| Tickets | Ticket's customer = source interaction's customer | 0 violators |
| Tickets | Ticket product = source interaction product | 0 violators |
| Tickets | `status = 'Resolved'` ⇔ `resolved_at` present; `resolved_at >= created_at` | 0 violators |
| Ownership | Every product a customer interacted about is in their `OWNS` set | 0 violators |
| Domains | `type`, `sentiment`, `status`, `priority`, `segment` within §5.2 enumerations; required properties non-null | 0 violators |
| Smoke | `customer_360` for `C001` returns 3 interactions, 1 ticket, 2 owned products | exact |

A representative violator-count check (pattern used by the cardinality group):

```cypher
MATCH (i:Interaction)
WHERE COUNT { (i)<-[:HAD_INTERACTION]-() } <> 1
   OR COUNT { (i)-[:VIA]->() }             <> 1
   OR COUNT { (i)-[:HANDLED_BY]->() }      <> 1
   OR COUNT { (i)-[:ABOUT]->() }           <> 1
RETURN count(i) AS violations;
```

---

## 12. PowerShell scripts

General rules for every script: `Set-StrictMode -Version Latest`, `$ErrorActionPreference = 'Stop'`, dot-source `common.ps1`, use `Set-ExecutionPolicy -Scope Process -Bypass` guidance in docs rather than changing machine policy, never echo the password, exit non-zero on failure with a clear message.

`common.ps1` provides: `.env` parser (skips comments, trims quotes), `NEO4J_HOME` resolution (env var → `.env`), `neo4j.version` reader, `Assert-Admin`, `Assert-Java` (major version from `java -version` vs `REQUIRED_JAVA_MAJOR`), `Assert-PortFree` / `Wait-Port` (TCP check on 7687 and 7474), and `Invoke-Python` (uses `.venv` if present).

### 12.1 `install-neo4j.ps1`
Input: path to the downloaded ZIP. Verify SHA-256 against `neo4j.version`, extract to the parent of `NEO4J_HOME`, confirm `bin\neo4j.bat`. Refuse to overwrite an existing install.

### 12.2 `setup.ps1` (first-time, idempotent)
1. Preflight: admin rights, Java version, `NEO4J_HOME` valid, Python ≥ 3.11, `.env` exists and `NEO4J_PASSWORD` is not `CHANGE_ME`.
2. Create `.venv` and `pip install -r requirements.txt` (skip if present).
3. Merge the managed config block (§8), replacing any previous block.
4. **Set the initial password before the first start**, only if the `neo4j` database has never been initialised (no `data\databases` content). Use the pinned release's admin command (for current releases `neo4j-admin dbms set-initial-password`; confirm with `--help`). If the database already exists, skip and rely on connectivity verification instead.
5. Install the service if absent (`bin\neo4j windows-service install`), set startup type (default Automatic; allow `-Manual` switch for laptops where always-on is unwanted).
6. Start the service, wait for Bolt (60 s timeout, then print the tail of the Neo4j log and fail).
7. Run `seed.ps1` (which runs `c360.seed`, including verification).
8. Print the Browser and Bolt endpoints.

### 12.3 Service lifecycle
`start-neo4j.ps1`, `stop-neo4j.ps1`, `restart-neo4j.ps1`, `status-neo4j.ps1` wrap `Start-Service` / `Stop-Service` / `Restart-Service` / `Get-Service` on `NEO4J_SERVICE_NAME`, and on start/restart wait for the port. `status` prints service state, both ports, and whether Bolt authenticates. `uninstall-service.ps1` stops the service and runs `bin\neo4j windows-service uninstall`; it never deletes install or data directories. `neo4j console` may be mentioned in docs for troubleshooting only.

Expected output after start:

```text
Neo4j started successfully.
Browser: http://localhost:7474
Bolt:    bolt://localhost:7687
```

### 12.4 `seed.ps1` / `verify.ps1`
Thin wrappers over `python -m c360.seed` and `python -m c360.verify` that propagate exit codes.

### 12.5 `reset-demo-data.ps1`
Requires `-Confirm` (or an interactive yes). Runs `python -m c360.reset`, which deletes only nodes carrying the six demo labels, in batches, and keeps constraints and indexes:

```cypher
MATCH (n) WHERE n:Customer OR n:Interaction OR n:Ticket OR n:Agent OR n:Channel OR n:Product
CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 1000 ROWS;
```

(If the pinned release rejects the scoped `CALL (n)` form, use the older `CALL { WITH n DETACH DELETE n } IN TRANSACTIONS` form.) It never touches installation files.

---

## 13. Application connectivity

`src/c360/config.py` loads `.env` (via `python-dotenv`), fails with a clear error if `NEO4J_PASSWORD` is missing, and exposes a driver factory. `app/examples/python_connection.py`:

```python
from neo4j import GraphDatabase
from c360.config import settings  # loads .env; raises if NEO4J_PASSWORD is missing

QUERY = """
MATCH (c:Customer)
RETURN c.customer_id AS customer_id, c.name AS name
ORDER BY c.customer_id
"""

with GraphDatabase.driver(settings.uri, auth=(settings.username, settings.password)) as driver:
    driver.verify_connectivity()
    records, _, _ = driver.execute_query(QUERY, database_=settings.database)
    for r in records:
        print(r["customer_id"], r["name"])
```

Expected output: `C001 Aarav Shah` … `C010 Simran Kapoor` (the ten names in §7.2).

Guidance for application code: create **one driver per process** and reuse it, pass values only as query parameters, and read nothing from Neo4j's data directory.

---

## 14. Security

- Bind to `127.0.0.1` only; do not forward or expose 7474/7687.
- Authentication on; strong local password in `.env` only; `.env` in `.gitignore`.
- The Windows service runs as `LocalSystem` by default (full local access). Acceptable for a laptop demo; for anything else, run it under a dedicated low-privilege service account.
- Synthetic data only. Do not load real customer data into this instance.
- Parameterised Cypher in all application code.
- Before the first commit, run a secrets check (`git grep -i password` and confirm `.env` is untracked).

---

## 15. Phased implementation (with gates)

Each phase ends with a gate command. Do not start the next phase until the gate passes. Pause and ask the user before any step that needs elevation or changes system state (service install, PATH or machine environment variables).

| Phase | Work | Gate |
|---|---|---|
| **P0** Decisions | Choose release; fill `neo4j.version`; read system-requirements and Windows pages for that release | G0, G0b (§4.3) |
| **P1** Skeleton | Repo layout, `.gitignore`, `.gitattributes`, `.env.example`, `requirements.txt`, README stub | `git status` clean of secrets; layout matches §6 |
| **P2** Install and config | `install-neo4j.ps1`, config block, `common.ps1` | `NEO4J_HOME\bin\neo4j.bat --version` prints the pinned version |
| **P3** Service | `setup.ps1` steps 1–6 and lifecycle scripts | `status-neo4j.ps1`: service running, 7687 reachable, auth works; stop → start survives; closing all terminals leaves Neo4j running |
| **P4** Data | Create all CSVs from §7; `data.py` validation; `tests/test_data.py` | `pytest` passes with no database running |
| **P5** Schema and loaders | `01_schema.cypher`, loaders, `06_chain.cypher`, `seed.py` | `seed.ps1` succeeds; counts equal §7.6 |
| **P6** Queries and verification | Query files, `verify.py` | `verify.ps1` exits 0; deliberately break one row (e.g. delete a `VIA`) and confirm exit 1, then restore |
| **P7** App example and docs | `python_connection.py`, README, `docs/` | Script prints the 10 customers |
| **P8** Hardening | Idempotency, reset, clean-machine run | §16 acceptance tests |

---

## 16. Acceptance tests and reproduction

### 16.1 Reproduction on another Windows laptop

```powershell
# 1. Install Git, the required JDK, Python 3.11+
# 2. Download the pinned Neo4j Community ZIP from the official Deployment Center, then:
git clone <repository-url>
cd customer-360-neo4j
copy .env.example .env            # edit: set NEO4J_PASSWORD and NEO4J_HOME
.\scripts\install-neo4j.ps1 -ZipPath <path-to-downloaded.zip>
.\scripts\setup.ps1               # elevated PowerShell
.\scripts\verify.ps1
python app\examples\python_connection.py
```

The database files are not copied between machines; the second machine recreates the same logical graph from Git.

### 16.2 Behavioural tests

| Test | Expected |
|---|---|
| Run `seed.ps1` twice | Counts and fingerprint (59 nodes, 160 relationships) unchanged |
| `reset-demo-data.ps1 -Confirm` then `seed.ps1` | Same fingerprint; constraints still present |
| Reboot the laptop (with Automatic startup) | Service running, no manual action |
| Two applications connected at once (e.g. the example script and Neo4j Browser/Query tool) | Both read the same data |
| Run `customer_360` for `C001` | 3 interactions, 1 ticket, 2 products |
| Run `channel_switches` | 15 `NEXT` pairs minus same-channel pairs, none crossing customers |

### 16.3 Clean-machine method
Use Windows Sandbox or a fresh Windows VM, install only the §4.2 prerequisites, then follow §16.1 verbatim and record any step that required undocumented knowledge. Fix the documentation, not the machine.

---

## 17. Definition of done

- [ ] Neo4j Community runs on Windows as a service; Docker not used.
- [ ] Bound to localhost; authentication enabled; password only in `.env`.
- [ ] Bolt reachable on 7687; Browser or documented alternative works (G0).
- [ ] 7 constraints and 3 indexes exist.
- [ ] 59 nodes and 160 relationships, matching §7.6.
- [ ] `NEXT` chains are per-customer, ordered, and derived (no hand-written pairs).
- [ ] `verify.ps1` passes and demonstrably fails on a broken graph.
- [ ] `pytest` data validation passes without a database.
- [ ] Seeding is idempotent; reset works and is label-scoped.
- [ ] Python example prints the 10 customers.
- [ ] Version pinned in exactly one file; README and docs reference it.
- [ ] No credentials or database files in Git.
- [ ] Reproduced on a clean machine (§16.3).

---

## 18. Future OmniResolve integration (context only)

```text
WhatsApp → OmniResolve API → LangGraph ──┬── Neo4j (Customer 360 context)
                                         ├── Vector DB (troubleshooting knowledge)
                                         └── Bedrock (reasoning)
                                                 → Resolved | Escalated
```

Neo4j answers who the customer is, what they own, what tickets and problems they have had, which channels and agents were involved, and what happened immediately before the current interaction (`latest_interaction.cypher`, keyed by the indexed `phone`). The vector DB answers how to troubleshoot; the LLM combines both.

The key boundary: **Neo4j is a shared database service, not a component embedded inside OmniResolve AI.**
