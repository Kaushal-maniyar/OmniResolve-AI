"""Short demo registration: name -> product -> CONFIRM. No email or consent gate."""
import re
from uuid import uuid4

PRODUCTS = {
    "1": ("P001", "Business Broadband"),
    "2": ("P002", "Internet Leased Line"),
    "3": ("P003", "SIP Trunk"),
    "4": ("P004", "Oracle SBC"),
    "5": ("P005", "Enterprise Wi-Fi"),
}
MENU = "\n".join(f"{key}. {name} ({pid})" for key, (pid, name) in PRODUCTS.items())


def handle_onboarding(driver, database, phone, message):
    """Persist registration state across worker restarts; never create OWNS."""
    if not re.fullmatch(r"[0-9]{8,15}", phone):
        raise ValueError("Invalid WhatsApp number")
    msg = (message or "").strip()
    lower = msg.casefold()
    with driver.session(database=database) as session:
        row = session.run(
            "MATCH (s:OnboardingSession {phone:$phone}) RETURN properties(s) AS data",
            phone=phone,
        ).single()
        data = row["data"] if row else {}
        step = data.get("step", "name")
        if lower == "cancel":
            session.run("MATCH (s:OnboardingSession {phone:$phone}) DELETE s", phone=phone).consume()
            return "Registration cancelled. Message us again whenever you're ready."
        if step == "name":
            # First incoming message may be a support question: do not save it as a name.
            if not row:
                session.run(
                    "MERGE (s:OnboardingSession {phone:$phone}) SET s.step='name'",
                    phone=phone,
                ).consume()
                return "Welcome to OmniResolve AI! To set up your demo profile, what's your name? (Reply CANCEL to stop.)"
            if not 2 <= len(msg) <= 80 or not re.fullmatch(r"[\w .'-]+", msg, re.UNICODE):
                return "Please enter your name (2–80 characters)."
            session.run(
                "MATCH (s:OnboardingSession {phone:$phone}) SET s.name=$name, s.step='product'",
                phone=phone, name=msg,
            ).consume()
            return "Thanks! Which product would you like to register for this demo?\n" + MENU
        if step == "product":
            selection = next((key for key, (pid, name) in PRODUCTS.items()
                              if lower in (key, pid.casefold(), name.casefold())), None)
            if selection is None:
                return "Please choose a product (number or code):\n" + MENU
            pid, name = PRODUCTS[selection]
            session.run(
                "MATCH (s:OnboardingSession {phone:$phone}) SET s.product_id=$pid, s.step='confirm'",
                phone=phone, pid=pid,
            ).consume()
            return (f"Confirm your demo registration:\nName: {data['name']}\n"
                    f"Product (self-reported): {name} ({pid})\n"
                    "Reply CONFIRM to save, or CANCEL to stop.")
        if step == "confirm":
            if lower != "confirm":
                return "Reply CONFIRM to finish registration or CANCEL to stop."
            customer_id = session.execute_write(_register, phone, "C-" + uuid4().hex[:16].upper())
            return (f"Demo registration complete! Your customer ID is {customer_id}. "
                    "How can I help you today?")
        raise RuntimeError("Unexpected registration step")


def _register(tx, phone, customer_id):
    existing = tx.run(
        "MATCH (c:Customer) WHERE c.phone IN [$phone, $plus_phone] RETURN c.id AS id LIMIT 2",
        phone=phone, plus_phone="+" + phone,
    ).data()
    if len(existing) > 1:
        raise RuntimeError("Multiple customer profiles share this phone number")
    if existing:
        tx.run("MATCH (s:OnboardingSession {phone:$phone}) DELETE s", phone=phone).consume()
        return existing[0]["id"]
    record = tx.run("""
        MATCH (s:OnboardingSession {phone:$phone})
        WHERE s.step='confirm' AND s.name IS NOT NULL AND s.product_id IS NOT NULL
        CREATE (c:Customer {
            id:$cid, name:s.name, phone:$phone,
            claimed_product_id:s.product_id,
            onboarding_status:'demo_registered',
            created_at:datetime()
        })
        DELETE s
        RETURN c.id AS id
    """, phone=phone, cid=customer_id).single()
    if not record:
        raise RuntimeError("Registration session missing; please start again")
    return record["id"]
