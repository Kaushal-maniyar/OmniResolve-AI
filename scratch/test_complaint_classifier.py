import json
from c360.agent.client import get_chat_model

llm = get_chat_model(temperature=0.0)

def classify(text):
    prompt = f'''You are an expert customer inquiry classifier.
Analyze the following customer message and determine if it contains a complaint, issue, fault, malfunction, or problem report about a product/service.
A simple greeting (e.g., 'Hi'), account inquiry ('How many tickets do I have?'), or generic question is NOT a complaint.
Any report of service interruption, slow speed, disconnect, audio issue, or broken device IS a complaint.

Respond with ONLY valid JSON:
{{"is_complaint": true/false, "reason": "brief explanation"}}

Message: "{text}"'''
    res = llm.invoke(prompt)
    print(f"'{text}' --> {res.content.strip()}")

for t in [
    "Hi",
    "How many open ticket do I have?",
    "My WiFi network is very slow and keeps dropping",
    "Business broadband is down with red LOS light",
    "Thank you for the help!"
]:
    classify(t)
