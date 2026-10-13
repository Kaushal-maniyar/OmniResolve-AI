param(
    [string]$Query = "My WiFi is not working",
    [string]$CustomerId = "C001",
    [string]$CustomerEmail = "",
    [string]$Channel = "whatsapp"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot "common.ps1")
Write-Host "Running LangGraph Customer Support Agent Workflow for Query: '$Query' [CustomerId: $CustomerId, Channel: $Channel]..."
Invoke-Python @("-c", "from c360.agent import run_agent_graph; import json; res = run_agent_graph('$Query', customer_id='$CustomerId', customer_email='$CustomerEmail', channel='$Channel'); print('\n=== AGENT RESPONSE ===\n' + res['final_response']); print('\n=== GRAPH STATE METADATA ==='); print(json.dumps({'product_id': res.get('product_id'), 'needs_escalation': res.get('needs_escalation'), 'ticket_created': res.get('ticket_created')}, indent=2))")
