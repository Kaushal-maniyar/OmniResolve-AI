from c360.agent.workflow import run_agent_graph

print("Starting OmniResolve agent...")

result = run_agent_graph(
    message_content="Hi, what products do I currently own?",
    customer_id="C001",
    channel="whatsapp",
    thread_id="whatsapp_local_test"
)

print("\n--- OMNIRESOLVE RESPONSE ---")
print(result)
