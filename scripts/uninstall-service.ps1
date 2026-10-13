Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot "common.ps1")
Assert-Admin

$envVars = Get-DotEnv
$serviceName = if ($envVars.ContainsKey("NEO4J_SERVICE_NAME")) { $envVars["NEO4J_SERVICE_NAME"] } else { "neo4j" }
$neo4jHome = Get-Neo4jHome

$svc = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($svc) {
    if ($svc.Status -eq "Running") {
        Write-Host "Stopping service '$serviceName'..."
        Stop-Service -Name $serviceName -Force
    }
    Write-Host "Uninstalling service '$serviceName'..."
    $neo4jBat = Join-Path $neo4jHome "bin\neo4j.bat"
    & $neo4jBat windows-service uninstall
    Write-Host "Service '$serviceName' uninstalled successfully. Installation and data files remain untouched."
} else {
    Write-Host "Service '$serviceName' is not installed."
}
