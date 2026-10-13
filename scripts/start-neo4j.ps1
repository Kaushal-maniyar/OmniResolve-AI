Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot "common.ps1")

$envVars = Get-DotEnv
$serviceName = if ($envVars.ContainsKey("NEO4J_SERVICE_NAME")) { $envVars["NEO4J_SERVICE_NAME"] } else { "neo4j" }
Assert-Java
$neo4jHome = Get-Neo4jHome
$neo4jBat = Join-Path $neo4jHome "bin\neo4j.bat"

$svc = Get-Service -Name $serviceName -ErrorAction SilentlyContinue

if ($svc) {
    Write-Host "Starting Neo4j Windows service '$serviceName'..."
    Start-Service -Name $serviceName
} else {
    Write-Host "Launching Neo4j server process in background..."
    Start-Process -FilePath $neo4jBat -ArgumentList "console" -WindowStyle Hidden
}

Write-Host "Waiting for Bolt port (7687)..."
if (Wait-Port -Address "127.0.0.1" -Port 7687 -TimeoutSeconds 60) {
    Write-Host "`nNeo4j started successfully!"
    Write-Host "Browser: http://localhost:7474"
    Write-Host "Bolt:    bolt://localhost:7687"
} else {
    Write-Error "Neo4j process launched but Bolt port 7687 did not respond within 60 seconds."
    exit 1
}
