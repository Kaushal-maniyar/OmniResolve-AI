import os
import json
import time
import logging
from collections import defaultdict, deque

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from groq import Groq
from c360.agent.workflow import run_agent_graph


# ============================================================
# 1. CONFIGURATION
# ============================================================

load_dotenv()

# Test-only: explicitly associate one WhatsApp sender
# with an existing fictional Neo4j customer.
TEST_WHATSAPP_NUMBER = os.getenv("TEST_WHATSAPP_NUMBER", "").lstrip("+")
TEST_CUSTOMER_ID = os.getenv("TEST_CUSTOMER_ID", "")

if TEST_WHATSAPP_NUMBER and not TEST_CUSTOMER_ID:
    raise RuntimeError(
        "TEST_CUSTOMER_ID is required when TEST_WHATSAPP_NUMBER is set."
    )

AWS_PROFILE = "omniresolve-dev"
AWS_REGION = "eu-north-1"

# Replace with your actual SQS queue URL.
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")

if not SQS_QUEUE_URL:
    raise RuntimeError("SQS_QUEUE_URL is missing from .env")

# Use the Meta API version that worked in your outbound test.
META_API_VERSION = "v20.0"

# You can change this to another model available in your Groq account.
GROQ_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
)

# Limit conversation history to avoid excessive token usage.
MAX_HISTORY_MESSAGES = 12

# SQS visibility timeout should exceed typical AI processing time.
VISIBILITY_TIMEOUT = 120

# Start with a single message per poll for easier debugging.
MAX_SQS_MESSAGES = 1


# ============================================================
# 2. LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("OmniResolve")


# ============================================================
# 3. AWS CLIENTS
# ============================================================

session = boto3.Session(
    profile_name=AWS_PROFILE,
    region_name=AWS_REGION
)

sqs = session.client("sqs")

whatsapp = session.client("socialmessaging")

# ============================================================
# 4. GROQ CLIENT
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is missing. Check your .env file."
    )

groq_client = Groq(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com"
)
# ============================================================
# 5. SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are OmniResolve AI, a helpful customer-support assistant
for a telecommunications service provider.

Your responsibilities include:

- Answering general telecom-related questions.
- Helping customers troubleshoot internet connectivity.
- Explaining common networking and telecom concepts.
- Assisting with Wi-Fi and router troubleshooting.
- Guiding customers through basic technical issues.
- Explaining how customers can seek additional support.

Communication guidelines:

- Be friendly, professional, and conversational.
- Keep WhatsApp responses relatively concise.
- Ask clarifying questions when necessary.
- Provide troubleshooting instructions step by step.
- Avoid unnecessarily technical explanations.
- Do not claim to have performed actions you cannot perform.

IMPORTANT SECURITY RULES:

- You do not have access to customer accounts.
- You cannot view customer products, subscriptions,
  bills, payments, or personal information.
- You cannot create or modify support tickets.
- You cannot access or change network infrastructure.
- You cannot verify a customer's identity.
- Never invent customer-specific information.
- Never ask customers to share passwords, OTPs,
  payment card details, or other sensitive credentials.

If a customer asks about their personal account,
explain that account verification and personalized
support are not yet available through this chatbot.

If an issue requires account access or a human agent,
explain that the customer should contact their
provider's authorized support channel.

You are currently operating in a general-support mode.
"""


# ============================================================
# 6. IN-MEMORY CONVERSATION STORAGE
# ============================================================

# Separate conversation history for every WhatsApp sender.
#
# Note: History resets whenever this script restarts.

conversations = defaultdict(
    lambda: deque(maxlen=MAX_HISTORY_MESSAGES)
)

# Track processed WhatsApp message IDs.
#
# Development-only deduplication:
# this set resets when the process restarts.

processed_message_ids = set()


# ============================================================
# 7. GENERATE AI RESPONSE
# ============================================================
def generate_ai_response(sender, user_message):

    normalized_sender = sender.lstrip("+")

    # Route only the explicitly configured test sender
    # to the customer-specific LangGraph workflow.
    if (
        TEST_WHATSAPP_NUMBER
        and normalized_sender == TEST_WHATSAPP_NUMBER
    ):
        logger.info(
            "Routing authorized test session to LangGraph | customer=%s",
            TEST_CUSTOMER_ID
        )

        result = run_agent_graph(
            message_content=user_message,
            customer_id=TEST_CUSTOMER_ID,
            channel="whatsapp",
            thread_id=f"whatsapp_{normalized_sender}"
        )

        reply = result.get("final_response")

        if not isinstance(reply, str) or not reply.strip():
            raise RuntimeError(
                "LangGraph returned an empty final_response."
            )

        return reply.strip()

    # All other senders retain the existing general-support chatbot.
    history = list(conversations[sender])

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    messages.extend(history)

    messages.append({
        "role": "user",
        "content": user_message
    })

    logger.info("Generating general-support response...")

    completion = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.5,
        max_tokens=500
    )

    reply = completion.choices[0].message.content

    if not reply:
        raise RuntimeError("Groq returned an empty response.")

    conversations[sender].append({
        "role": "user",
        "content": user_message
    })

    conversations[sender].append({
        "role": "assistant",
        "content": reply
    })

    return reply

# ============================================================
# 8. SEND WHATSAPP MESSAGE
# ============================================================


def send_whatsapp_message(
    recipient,
    business_phone_arn,
    text
):

    # The successful outbound test used the +country-code format.
    recipient = "+" + recipient.lstrip("+")

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": text[:4096]
        }
    }

    response = whatsapp.send_whatsapp_message(
        originationPhoneNumberId=business_phone_arn,
        message=json.dumps(payload).encode("utf-8"),
        metaApiVersion=META_API_VERSION
    )

    logger.info(
        "WhatsApp send accepted | messageId=%s",
        response.get("messageId")
    )

    return response


# ============================================================
# 9. DECODE SQS MESSAGE
# ============================================================

def decode_sqs_message(sqs_message):

    body = json.loads(sqs_message["Body"])

    # SNS usually wraps the original AWS event.
    if "Message" in body:
        event = json.loads(body["Message"])
    else:
        event = body

    webhook_entry = event.get("whatsAppWebhookEntry")

    if not webhook_entry:
        return None, []

    if isinstance(webhook_entry, str):
        webhook = json.loads(webhook_entry)
    else:
        webhook = webhook_entry

    phone_numbers = (
        event.get("context", {})
        .get("MetaPhoneNumberIds", [])
    )

    if not phone_numbers:
        raise ValueError(
            "No business phone ARN found in incoming event."
        )

    business_phone_arn = phone_numbers[0].get("arn")

    if not business_phone_arn:
        raise ValueError(
            "Business phone ARN is missing."
        )

    incoming_messages = []

    for change in webhook.get("changes", []):

        value = change.get("value", {})

        for message in value.get("messages", []):

            incoming_messages.append({
                "sender": message.get("from"),
                "message_id": message.get("id"),
                "message_type": message.get("type"),
                "text": message.get("text", {}).get("body"),
                "business_phone_arn": business_phone_arn
            })

    return event, incoming_messages


# ============================================================
# 10. PROCESS INCOMING WHATSAPP MESSAGE
# ============================================================

def process_whatsapp_message(message):

    sender = message["sender"]
    message_id = message["message_id"]
    message_type = message["message_type"]
    text = message["text"]
    business_phone_arn = message["business_phone_arn"]

    if not sender or not message_id:
        logger.warning("Skipping malformed WhatsApp message.")
        return

    if message_id in processed_message_ids:
        logger.info("Duplicate message skipped: %s", message_id)
        return

    if message_type != "text":
        logger.info(
            "Unsupported message type from %s: %s",
            sender,
            message_type
        )

        # For now, we only support text messages.
        processed_message_ids.add(message_id)
        return

    if not text or not text.strip():
        logger.info("Skipping empty text message.")
        processed_message_ids.add(message_id)
        return

    logger.info("----------------------------------------")
    logger.info("Incoming WhatsApp message")
    logger.info("Sender: %s", sender)
    logger.info("Message ID: %s", message_id)
    logger.info("Text: %s", text)

    # Generate AI reply.
    reply = generate_ai_response(
        sender=sender,
        user_message=text
    )

    logger.info("AI Reply: %s", reply)

    # Send the reply to the same WhatsApp sender.
    send_whatsapp_message(
        recipient=sender,
        business_phone_arn=business_phone_arn,
        text=reply
    )

    # Mark processed only after AWS accepts the outgoing message.
    processed_message_ids.add(message_id)

    logger.info("Message processed successfully.")


# ============================================================
# 11. PROCESS SQS EVENTS
# ============================================================

def process_sqs_event(sqs_message):

    event, incoming_messages = decode_sqs_message(
        sqs_message
    )

    if not incoming_messages:
        logger.info(
            "No incoming WhatsApp text messages in event."
        )
        return

    for message in incoming_messages:
        process_whatsapp_message(message)


# ============================================================
# 12. CONTINUOUS SQS POLLING
# ============================================================

def start_worker():

    logger.info("========================================")
    logger.info("OmniResolve WhatsApp Worker Started")
    logger.info("AWS Region: %s", AWS_REGION)
    logger.info("Groq Model: %s", GROQ_MODEL)
    logger.info("Waiting for WhatsApp messages...")
    logger.info("========================================")

    while True:

        try:

            response = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=MAX_SQS_MESSAGES,
                WaitTimeSeconds=20,
                VisibilityTimeout=VISIBILITY_TIMEOUT
            )

            messages = response.get("Messages", [])

            if not messages:
                continue

            for sqs_message in messages:

                try:

                    process_sqs_event(sqs_message)

                    # Delete only after successful processing.
                    sqs.delete_message(
                        QueueUrl=SQS_QUEUE_URL,
                        ReceiptHandle=sqs_message["ReceiptHandle"]
                    )

                    logger.info(
                        "SQS message deleted successfully."
                    )

                except Exception:
                    logger.exception(
                        "Failed to process SQS message. "
                        "It will become visible again."
                    )

        except KeyboardInterrupt:
            logger.info("Stopping OmniResolve worker...")
            break

        except ClientError:
            logger.exception("AWS error while polling SQS.")
            time.sleep(5)

        except Exception:
            logger.exception("Unexpected worker error.")
            time.sleep(5)


# ============================================================
# 13. ENTRY POINT
# ============================================================

if __name__ == "__main__":
    start_worker()
