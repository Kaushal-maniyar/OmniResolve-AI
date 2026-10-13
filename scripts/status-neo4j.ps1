Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot "common.ps1")

$envVars = Get-DotEnv
$serviceName = if ($envVars.ContainsKey("NEO4J_SERVICE_NAME")) { $envVars["NEO4J_SERVICE_NAME"] } else { "neo4j" }

$svc = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($svc) {
    Write-Host "Service '$serviceName' Status: $($svc.Status) (StartupType: $($svc.StartType))"
} else {
    Write-Host "Service '$serviceName' is NOT installed as a Windows Service."
}

$boltUp = Wait-Port -Address "127.0.0.1" -Port 7687 -TimeoutSeconds 2
$httpUp = Wait-Port -Address "127.0.0.1" -Port 7474 -TimeoutSeconds 2

Write-Host "Bolt Listener (7687): $(if ($boltUp) { 'UP' } else { 'DOWN' })"
Write-Host "HTTP Listener (7474): $(if ($httpUp) { 'UP' } else { 'DOWN' })"

if ($boltUp) {
    Write-Host "`nTesting Bolt Authentication..."
    Invoke-Python @("-c", "from c360.config import settings; d = settings.get_driver(); d.verify_connectivity(); d.close(); print('Bolt Auth: SUCCESS')")
} else {
    Write-Host "`nNeo4j is currently NOT running."
}
