param(
    [string]$CustomerId = "C001"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot "common.ps1")
Write-Host "Launching Interactive WhatsApp Customer Support Chat Session..."
Invoke-Python @("-m", "c360.agent.chat", $CustomerId)
