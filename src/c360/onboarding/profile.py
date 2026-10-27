"""Demo-only, support-first WhatsApp profile creation and conservative enrichment."""
import re
from uuid import uuid4

PRODUCTS = {
    'P001': 'Business Broadband',
    'P002': 'Internet Leased Line',
    'P003': 'SIP Trunk',
    'P004': 'Oracle SBC',
    'P005': 'Enterprise WiFi',
}


def get_or_create_customer(driver, database, phone):
    """Atomic, phone-keyed creation; requires unique Customer.phone constraint."""
    if not re.fullmatch(r'[0-9]{8,15}', phone):
        raise ValueError('Invalid WhatsApp sender phone')
    with driver.session(database=database) as session:
        return session.execute_write(_get_or_create, phone)


def _get_or_create(tx, phone):
    # Existing demo records may have a '+' prefix; do not create duplicates.
    rows = list(tx.run('''
        MATCH (c:Customer)
        WHERE c.phone IN [$phone, $plus_phone]
        RETURN c.id AS id LIMIT 2
    ''', phone=phone, plus_phone='+' + phone))
    if len(rows) > 1:
        raise RuntimeError('Ambiguous customer phone mapping')
    if rows:
        return rows[0]['id']
    # MERGE is protected by Customer.phone uniqueness constraint.
    record = tx.run('''
        MERGE (c:Customer {phone: $phone})
        ON CREATE SET c.id = $id, c.created_at = datetime(),
                      c.profile_status = 'incomplete',
                      c.onboarding_status = 'self_registered'
        RETURN c.id AS id
    ''', phone=phone, id='C-' + uuid4().hex.upper()).single()
    if not record or not record['id']:
        raise RuntimeError('Customer creation failed')
    return record['id']


def capture_explicit_profile_details(driver, database, customer_id, message):
    """Save only explicitly supplied name/product; never claim verified ownership."""
    text = (message or '').strip()
    name = None
    m = re.search(
        r"\b(?:my name is|i am|i'm)\s+([A-Za-z][A-Za-z .'-]{1,60})", text, re.I)
    if m:
        candidate = re.split(r'[.!?,\n]|\s+(?:and|my|because|with)\b',
                             m.group(1), maxsplit=1, flags=re.I)[0].strip()
        if 2 <= len(candidate) <= 60:
            name = candidate
    product_id = None
    for pid, pname in PRODUCTS.items():
        if re.search(r'\b(?:i use|i have|my|our|we use)\s+(?:an?\s+)?' + re.escape(pname) + r'\b', text, re.I):
            product_id = pid
            break
    if not name and not product_id:
        return
    with driver.session(database=database) as session:
        session.run('''
            MATCH (c:Customer {id: $cid})
            SET c.name = CASE WHEN $name IS NULL THEN c.name ELSE $name END,
                c.claimed_product_id = CASE WHEN $pid IS NULL THEN c.claimed_product_id ELSE $pid END
        ''', cid=customer_id, name=name, pid=product_id).consume()
