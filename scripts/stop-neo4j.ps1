Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot "common.ps1")
Assert-Admin

$envVars = Get-DotEnv
$serviceName = if ($envVars.ContainsKey("NEO4J_SERVICE_NAME")) { $envVars["NEO4J_SERVICE_NAME"] } else { "neo4j" }

Write-Host "Stopping Neo4j service '$serviceName'..."
Stop-Service -Name $serviceName -Force
Write-Host "Neo4j service stopped successfully."
