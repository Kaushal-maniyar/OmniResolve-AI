# OmniResolve AI

### Agentic telecom customer support, delivered through WhatsApp

OmniResolve AI is a **hackathon prototype** that connects WhatsApp conversations to an AI-powered telecom support workflow. It combines **AWS End User Messaging Social (WhatsApp)**, **Amazon SNS**, **Amazon SQS**, **LangGraph**, a configured LLM provider, a troubleshooting knowledge retriever, and a **Neo4j Customer 360 graph**.

Customers can register for a demo, ask telecom questions, receive troubleshooting assistance, and request support tickets. The project demonstrates how an asynchronous messaging pipeline can connect a familiar customer channel to contextual support tools.

> **Project status:** Local Python worker and local Neo4j database; AWS messaging services handle inbound and outbound WhatsApp communication. This is a demo, not a production identity-verification or telecom-provisioning system. End-to-end behavior should be verified on the final code revision before submission.

## Architecture

![OmniResolve AI architecture](docs/architecture.svg)

**Inbound:** WhatsApp customer → AWS End User Messaging Social → Amazon SNS → Amazon SQS → Python worker.

**Processing:** The worker checks the sender against Neo4j. Unknown senders follow short demo registration; known senders enter a LangGraph support workflow. LangGraph uses the configured LLM and tools for Customer 360 retrieval, knowledge retrieval, attachment metadata lookup, and ticket creation.

**Outbound:** The worker sends responses through the AWS End User Messaging Social `send_whatsapp_message` API → WhatsApp customer.

The Python worker and Neo4j instance are currently **local**, not deployed to AWS compute or a managed Neo4j service.

## Features

| Capability | Functionality |
|---|---|
| WhatsApp-native interaction | Customers send and receive messages in WhatsApp; no separate front end is required. |
| AWS event-driven messaging | SNS forwards inbound events to SQS; the Python worker polls the queue and processes messages. |
| Short demo registration | Unknown numbers provide a name, select a demo product, and reply `CONFIRM`. Email is not required. |
| Customer 360 context | Neo4j stores customers, products, interactions, complaints, and tickets; agent tools retrieve related records. |
| AI troubleshooting | LangGraph orchestrates LLM reasoning and knowledge-base retrieval for telecom support questions. |
| Multi-turn support | LangGraph uses an in-memory checkpointer keyed by WhatsApp conversation thread. |
| Ticket escalation | A ticket tool persists support tickets in Neo4j; the latest demo workflow gates tool execution behind `CONFIRM TICKET`. |
| Conversation ingestion | Incoming customer messages and outgoing agent responses are ingested into Neo4j. |
| Media metadata lookup | An agent tool can retrieve stored image/video attachment metadata from Neo4j; the current WhatsApp worker handles **text messages only**. |

### Example customer journey

1. A new customer sends a WhatsApp message.
2. OmniResolve requests their **name**, **demo product**, and **registration confirmation**.
3. After registration, the customer describes an internet or telecom issue.
4. The LangGraph agent consults the knowledge retriever and available Customer 360 context.
5. If escalation is needed, the agent can propose a support ticket; the customer replies **`CONFIRM TICKET`** before the ticket tool is allowed to run.
6. The ticket is saved to Neo4j and the result is returned over WhatsApp.

**Important:** Selecting a product at registration records a *claimed product*, not verified ownership. A ticket is an escalation record; the demo does **not** actually provision services or modify telecom infrastructure.

## AWS CDS integration (runtime usage)

The project uses **AWS End User Messaging Social (WhatsApp)** as its qualifying AWS Customer Delivery Service integration. It is called by the running application, not only shown in the architecture diagram.

The WhatsApp worker initializes the AWS client using `boto3`:

```python
session = boto3.Session(profile_name="omniresolve-dev", region_name="eu-north-1")
sqs = session.client("sqs")
whatsapp = session.client("socialmessaging")
```

It polls SQS with `sqs.receive_message(...)`, decodes the inbound WhatsApp webhook event, and sends replies using:

```python
whatsapp.send_whatsapp_message(
    originationPhoneNumberId=business_phone_arn,
    message=json.dumps(payload).encode("utf-8"),
    metaApiVersion=META_API_VERSION,
)
```

This design uses AWS to deliver inbound messages and outbound responses while separating message transport from AI processing. **Amazon SNS and SQS are supporting services; AWS End User Messaging Social is the qualifying WhatsApp integration.**

## Technology stack

- **Messaging:** WhatsApp, AWS End User Messaging Social, Amazon SNS, Amazon SQS, `boto3`
- **Agent orchestration:** Python, LangGraph, LangChain tools, in-memory checkpointing
- **LLM:** Configured chat-model provider (Groq used in development; fallback configuration exists)
- **Customer data:** Neo4j graph database, Cypher
- **Knowledge:** Project knowledge-base retriever
- **Local development:** Windows PowerShell, Python virtual environment

## Repository structure (relevant paths)

```text
OmniResolve-AI/
├── whatsapp_worker.py                   # AWS SQS → WhatsApp processing
├── src/c360/agent/
│   ├── workflow.py                      # LangGraph and ticket confirmation gate
│   ├── nodes.py                         # Message ingestion, LLM, response ingestion
│   └── tools.py                         # Customer 360, KB, media, tickets
├── src/c360/onboarding/
│   ├── __init__.py
│   └── registration.py                  # Short demo registration
├── cypher/01_schema.cypher              # Schema constraints and indexes
├── data/                                # Seed/demo CSV data
├── scripts/                             # Neo4j helper scripts
└── docs/
    ├── architecture.svg
    └── architecture.png
```

## Local interaction instructions

**Prerequisites:** Python environment with project dependencies, working Neo4j instance, configured AWS credentials with access to the WhatsApp messaging resources, and a configured LLM provider. Follow the repository's existing Neo4j setup instructions for first-time initialization.

1. Configure the application's environment variables and AWS credentials **locally**. Do not commit `.env`, secrets, real customer numbers, or private message logs.
2. Start Neo4j and ensure the demo schema and required agent/product records exist.
3. From the project root on Windows PowerShell, start the worker:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH="$PWD\src"
python whatsapp_worker.py
```

4. Send a **text** message to the configured WhatsApp business/test number. A new number enters short demo registration; a registered number enters the AI support flow.
5. To test escalation, describe a support issue, review the proposed ticket, then reply `CONFIRM TICKET`.

**Warning:** `src/c360/graph/seed.py` purges the current graph and schema before loading seed data. **Do not rerun it against a database containing records you need to keep.** Git stores the setup scripts and CSV fixtures, **not** a live Neo4j database snapshot.

## Demo / submission links

- **Repository:** https://github.com/Kaushal-maniyar/OmniResolve-AI (use the final submitted branch/commit)
- **Demo video:** _Add public YouTube or Vimeo URL_
- **Live web URL:** Not applicable to this local-worker prototype; use the repository and interaction instructions above.
- **ACE Opportunity ID:** _Add the net-new ACE ID from AWS Partner Central, with the required campaign code_

## Security and current limitations

- The demo's WhatsApp phone-to-customer mapping is **not production-grade identity verification**.
- Customer-specific tools currently accept LLM-supplied customer IDs; production deployment requires strict tool-level scoping to an authenticated customer identity.
- The ticket confirmation gate checks for `CONFIRM TICKET` in the current message; it is a **demo safeguard**, not a complete authorization or ticket-approval system.
- In-memory LangGraph checkpoints and message deduplication do not survive worker restarts.
- The worker currently handles **text** WhatsApp messages, not inbound media content.
- Product selection during registration does not establish a verified `OWNS` relationship.
- The current worker and Neo4j database run locally; there is no always-on public service URL.

## Hackathon submission

This project demonstrates a qualifying WhatsApp integration through **AWS End User Messaging Social**, with an event-driven SNS/SQS processing path, an AI support workflow, and Neo4j-backed Customer 360 context. Include a public demo video, the final repository link, and the required **ACE Opportunity ID** in the submission form.
