import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest
from c360.agent import run_agent_graph, CustomerSupportGraph, VLLMClient

def test_vllm_client_initialization():
    """Verify VLLMClient initializes with configured settings."""
    client = VLLMClient()
    assert client.base_url == "http://192.168.100.10:8000/v1"
    assert client.model == "qwen3.8-27b"
    assert client.api_key == "llm-engineer-dev-key-change-in-prod"

def test_turn1_basic_troubleshooting_without_ticket():
    """Verify Turn 1 returns basic troubleshooting steps without creating a ticket."""
    thread_id = "test_thread_turn1"
    res = run_agent_graph("My WiFi network is slow", customer_id="C001", channel="whatsapp", thread_id=thread_id)
    assert "final_response" in res
    assert res.get("needs_escalation") is False
    assert res.get("ticket_created") is None
    response_text = res["final_response"]
    assert "1." in response_text or "diagnostic" in response_text.lower() or "WiFi" in response_text

def test_turn2_conditional_ticket_creation_on_issue_persistence():
    """Verify Turn 2 generates a ticket when customer confirms issue persists after troubleshooting."""
    thread_id = "test_thread_turn2"
    # Turn 1: Initial question
    res1 = run_agent_graph("My Business Broadband is down", customer_id="C001", channel="whatsapp", thread_id=thread_id)
    assert res1.get("ticket_created") is None

    # Turn 2: Customer reports issue persists after trying troubleshooting
    res2 = run_agent_graph("I tried all the troubleshooting steps but the issue still persists", customer_id="C001", channel="whatsapp", thread_id=thread_id)
    assert res2.get("needs_escalation") is True
    ticket = res2.get("ticket_created")
    assert ticket is not None
    assert ticket["id"].startswith("TCK-")
    assert "Escalated" in ticket["status"]

def test_authenticated_customer_ticket_lookup_without_asking_id():
    """Verify that when customer asks for open tickets, agent uses session customer_id C001 directly without asking for ID."""
    thread_id = "test_thread_ticket_lookup"
    res = run_agent_graph("How many open ticket do I have?", customer_id="C001", channel="whatsapp", thread_id=thread_id)
    response_text = res.get("final_response", "")
    # Must NOT ask for customer ID or email
    assert "provide your customer id" not in response_text.lower()
    assert "need to know your customer id" not in response_text.lower()
    assert "could you please provide" not in response_text.lower()
    # Must answer with ticket status / count
    assert "0" in response_text or "ticket" in response_text.lower()

