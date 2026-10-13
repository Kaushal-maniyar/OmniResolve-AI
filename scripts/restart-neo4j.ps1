Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot "common.ps1")
Assert-Admin

$envVars = Get-DotEnv
$serviceName = if ($envVars.ContainsKey("NEO4J_SERVICE_NAME")) { $envVars["NEO4J_SERVICE_NAME"] } else { "neo4j" }

Write-Host "Restarting Neo4j service '$serviceName'..."
Restart-Service -Name $serviceName -Force

Write-Host "Waiting for Bolt port (7687)..."
if (Wait-Port -Address "127.0.0.1" -Port 7687 -TimeoutSeconds 60) {
    Write-Host "Neo4j restarted successfully."
    Write-Host "Browser: http://localhost:7474"
    Write-Host "Bolt:    bolt://localhost:7687"
} else {
    Write-Error "Neo4j service restarted but Bolt port 7687 did not respond in time."
    exit 1
}
