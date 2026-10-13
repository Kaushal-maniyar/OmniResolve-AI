import csv
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"

VALID_TICKET_STATUSES = {"Open", "In Progress", "Escalated", "Resolved"}
VALID_COMPLAINT_STATUSES = {"Open", "Investigating", "Resolved"}
VALID_AGENT_TYPES = {"Human", "LLM"}

def read_csv(filename: str) -> list[dict]:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Required CSV file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            cleaned = {}
            for k, v in row.items():
                if k is None:
                    continue
                if isinstance(v, str):
                    cleaned[k] = v.strip() if v.strip() != "" else None
                elif isinstance(v, list):
                    cleaned[k] = [item.strip() for item in v if isinstance(item, str) and item.strip() != ""]
                else:
                    cleaned[k] = v
            rows.append(cleaned)
        return rows

def validate_datasets():
    customers = read_csv("customers.csv")
    products = read_csv("products.csv")
    agents = read_csv("agents.csv")
    complaints = read_csv("complaints.csv")
    tickets = read_csv("tickets.csv")
    messages = read_csv("messages.csv")
    emails = read_csv("emails.csv")
    images = read_csv("images.csv")
    videos = read_csv("videos.csv")

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

    customer_ids = {c["id"] for c in customers}
    product_ids = {p["id"] for p in products}
    agent_ids = {a["id"] for a in agents}
    complaint_ids = {cmp["id"] for cmp in complaints}
    ticket_ids = {t["id"] for t in tickets}
    message_ids = {m["id"] for m in messages}
    email_ids = {e["id"] for e in emails}
    image_ids = {img["id"] for img in images}
    video_ids = {v["id"] for v in videos}

    # Check Primary Keys
    assert len(customers) == len(customer_ids), "Duplicate customer id found"
    assert len(products) == len(product_ids), "Duplicate product id found"
    assert len(agents) == len(agent_ids), "Duplicate agent id found"
    assert len(complaints) == len(complaint_ids), "Duplicate complaint id found"
    assert len(tickets) == len(ticket_ids), "Duplicate ticket id found"
    assert len(messages) == len(message_ids), "Duplicate message id found"
    assert len(emails) == len(email_ids), "Duplicate email id found"
    assert len(images) == len(image_ids), "Duplicate image id found"
    assert len(videos) == len(video_ids), "Duplicate video id found"

    # Validate Enums & Values
    for a in agents:
        assert a["type"] in VALID_AGENT_TYPES, f"Invalid agent type: {a['type']}"
    for cmp in complaints:
        assert cmp["status"] in VALID_COMPLAINT_STATUSES, f"Invalid complaint status: {cmp['status']}"
    for t in tickets:
        assert t["status"] in VALID_TICKET_STATUSES, f"Invalid ticket status: {t['status']}"

    # Foreign Key Resolutions
    for o in owns:
        assert o["customer_id"] in customer_ids, f"OWNS has invalid customer_id: {o['customer_id']}"
        assert o["product_id"] in product_ids, f"OWNS has invalid product_id: {o['product_id']}"
    for sm in sent_messages:
        assert sm["customer_id"] in customer_ids, f"SENT message has invalid customer_id: {sm['customer_id']}"
        assert sm["message_id"] in message_ids, f"SENT message has invalid message_id: {sm['message_id']}"
    for se in sent_emails:
        assert se["customer_id"] in customer_ids, f"SENT email has invalid customer_id: {se['customer_id']}"
        assert se["email_id"] in email_ids, f"SENT email has invalid email_id: {se['email_id']}"
    for li in last_interaction:
        assert li["customer_id"] in customer_ids, f"LAST_INTERACTION has invalid customer_id: {li['customer_id']}"
        assert li["email_id"] in email_ids, f"LAST_INTERACTION has invalid email_id: {li['email_id']}"
    for ags in agent_sent:
        assert ags["agent_id"] in agent_ids, f"Agent SENT message has invalid agent_id: {ags['agent_id']}"
        assert ags["message_id"] in message_ids, f"Agent SENT message has invalid message_id: {ags['message_id']}"
    for r in raises:
        assert r["agent_id"] in agent_ids, f"RAISE has invalid agent_id: {r['agent_id']}"
        assert r["ticket_id"] in ticket_ids, f"RAISE has invalid ticket_id: {r['ticket_id']}"
    for cy in complaint_yes:
        assert cy["complaint_id"] in complaint_ids, f"YES has invalid complaint_id: {cy['complaint_id']}"
        assert cy["message_id"] in message_ids, f"YES has invalid message_id: {cy['message_id']}"
    for mc in message_chain:
        assert mc["prev_message_id"] in message_ids, f"NEXT/PRE chain invalid prev_message_id: {mc['prev_message_id']}"
        assert mc["next_message_id"] in message_ids, f"NEXT/PRE chain invalid next_message_id: {mc['next_message_id']}"
    for m2e in message_to_email:
        assert m2e["message_id"] in message_ids, f"NEXT/PRE message-email invalid message_id: {m2e['message_id']}"
        assert m2e["email_id"] in email_ids, f"NEXT/PRE message-email invalid email_id: {m2e['email_id']}"
    for att in has_attachments:
        if att["source_type"] == "Message":
            assert att["source_id"] in message_ids
        elif att["source_type"] == "Email":
            assert att["source_id"] in email_ids
        if att["attachment_type"] == "Image":
            assert att["attachment_id"] in image_ids
        elif att["attachment_type"] == "Video":
            assert att["attachment_id"] in video_ids
    for ast in associated_tickets:
        assert ast["message_id"] in message_ids, f"ASSOCIATED has invalid message_id: {ast['message_id']}"
        assert ast["ticket_id"] in ticket_ids, f"ASSOCIATED has invalid ticket_id: {ast['ticket_id']}"
    for tc in ticket_complaint:
        assert tc["ticket_id"] in ticket_ids, f"ASSOCIATED ticket-complaint invalid ticket_id: {tc['ticket_id']}"
        assert tc["complaint_id"] in complaint_ids, f"ASSOCIATED ticket-complaint invalid complaint_id: {tc['complaint_id']}"

    print("All handwritten schema CSV datasets validated successfully.")

if __name__ == "__main__":
    validate_datasets()
