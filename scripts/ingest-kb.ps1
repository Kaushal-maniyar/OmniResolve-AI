Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot "common.ps1")
Write-Host "Running Knowledge Base Ingestion & GraphRAG Sync..."
Invoke-Python @("-m", "c360.knowledge.ingest")
