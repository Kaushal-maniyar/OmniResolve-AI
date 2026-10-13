Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot "common.ps1")
Write-Host "Running graph invariant verification..."
Invoke-Python @("-m", "c360.graph.verify")
