import sys
import uuid
import time
from c360.agent.workflow import run_agent_graph

def start_interactive_whatsapp_chat(customer_id: str = "C001", channel: str = "whatsapp"):
    """Start an interactive real-time console chat simulating WhatsApp Customer Support."""
    thread_id = f"wa_thread_{str(uuid.uuid4())[:6]}"
    
    print("\n" + "=" * 65)
    print("      [ WhatsApp Customer Support - OmniResolve AI ]      ")
    print("=" * 65)
    print(f" Connected Customer ID : {customer_id}")
    print(f" Active Channel        : {channel.upper()}")
    print(f" Session Thread ID     : {thread_id}")
    print("-" * 65)
    print(" Instructions:")
    print("  - Type your message to start chatting.")
    print("  - Perform basic troubleshooting when guided.")
    print("  - Reply 'issue persists' or 'didn't work' if troubleshooting fails.")
    print("  - Type 'exit' or 'quit' to end session.")
    print("=" * 65 + "\n")

    turn = 1

    while True:
        try:
            user_input = input(f"\n[Customer ({customer_id})] > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "q"]:
                print("\n[WhatsApp] Customer ended chat session. Goodbye!")
                break

            print("\n  ... [OmniResolve AI Support Agent is typing...] ...")
            time.sleep(0.5)

            # Run LangGraph Agent Workflow
            res = run_agent_graph(
                message_content=user_input,
                customer_id=customer_id,
                channel=channel,
                thread_id=thread_id
            )

            response = res.get("final_response", "")
            ticket = res.get("ticket_created")
            product_id = res.get("product_id")

            print("\n" + "-" * 65)
            print(f"[OmniResolve AI Support Agent (Turn {turn})]")
            if product_id:
                print(f" Focus Product: {product_id}")
            print("-" * 65)
            print(response.strip())

            if ticket:
                print("\n" + "*" * 65)
                print(" [SYSTEM EVENT: SUPPORT TICKET CREATED IN NEO4J GRAPH]")
                print(f"  Ticket ID : {ticket.get('id')}")
                print(f"  Status    : {ticket.get('status')}")
                print(f"  Priority  : {ticket.get('priority')}")
                print("*" * 65)

            turn += 1

        except KeyboardInterrupt:
            print("\n\n[WhatsApp] Chat session terminated by user.")
            break
        except Exception as e:
            print(f"\n[Error] An error occurred during chat execution: {e}")

if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "C001"
    start_interactive_whatsapp_chat(customer_id=cid)
