param(
    [string]$Query = "My WiFi is not working",
    [string]$ProductId = "",
    [int]$TopK = 15
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot "common.ps1")
Write-Host "Querying Knowledge Base Vector Store for: '$Query' [ProductId: $(if ($ProductId) { $ProductId } else { 'Auto-Detect' }), TopK: $TopK]..."
Invoke-Python @("-c", "from c360.knowledge.retriever import retriever; import json; res = retriever.retrieve('$Query', product_id='$ProductId', top_k=$TopK); print(json.dumps(res, indent=2))")
