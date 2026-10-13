Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot "common.ps1")
Write-Host "Seeding database..."
Invoke-Python @("-m", "c360.graph.seed")
