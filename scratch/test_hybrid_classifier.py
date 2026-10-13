import json
import re
from c360.agent.client import get_chat_model

FAST_NEGATIVE = [
    r"^\s*(hi|hello|hey|good\s+morning|good\s+afternoon|good\s+evening|hi\s+there)\b",
    r"^\s*how\s+many\s+(open\s+)?tickets?",
    r"^\s*(check|show|what\s+are)\s+(my\s+)?tickets?",
    r"^\s*(thank\s+you|thanks|bye|goodbye|ok|okay)\s*$"
]

FAST_POSITIVE = [
    "not working", "is down", "down", "stopped working", "disconnected", "disconnecting",
    "slow speed", "slow", "high ping", "packet loss", "los light", "red light",
    "one way audio", "one-way audio", "call drop", "call drops", "registration fail",
    "broken", "complaint", "issue persist", "still not working", "failed to connect",
    "cannot connect", "cant connect", "authentication error", "no internet", "fault", "intermittent"
]

def classify_message_complaint(text: str) -> bool:
    clean = text.strip().lower()
    
    # 1. Fast negative regex
    for pat in FAST_NEGATIVE:
        if re.search(pat, clean):
            return False

    # 2. Fast positive keywords
    for kw in FAST_POSITIVE:
        if kw in clean:
            return True

    # 3. LLM classification fallback
    try:
        llm = get_chat_model(temperature=0.0)
        prompt = f"""You are an expert telecommunications customer complaint classifier.
Analyze the customer message and decide if it expresses a complaint, problem report, or malfunction about a product or service.
A greeting or inquiry is NOT a complaint.
Respond with JSON: {{\"is_complaint\": true/false}}

Customer message: "{text}"
"""
        res = llm.invoke(prompt)
        data = json.loads(res.content.strip().strip("```json").strip("```"))
        return bool(data.get("is_complaint", False))
    except Exception:
        return False

# Test run
test_cases = [
    ("Hi", False),
    ("How many open ticket do I have?", False),
    ("My WiFi network is slow", True),
    ("Business broadband is down", True),
    ("What products do I have?", False),
    ("I am experiencing frequent call drops on SIP trunk", True),
    ("Thanks for the update", False)
]

for text, expected in test_cases:
    actual = classify_message_complaint(text)
    status = "PASS" if actual == expected else "FAIL"
    print(f"[{status}] '{text}' => {actual} (Expected: {expected})")
