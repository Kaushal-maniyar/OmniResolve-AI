param(
    [switch]$ManualStartup
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot "common.ps1")

Write-Host "=== 1. PREFLIGHT CHECKS ==="
$isAdmin = Assert-Admin
Assert-Java

$envVars = Get-DotEnv
$neo4jHome = Get-Neo4jHome

if (-not (Test-Path $neo4jHome)) {
    Write-Host "Neo4j home not found at $neo4jHome. Running installer..."
    powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "install-neo4j.ps1")
}

Write-Host "=== 2. PYTHON VIRTUAL ENVIRONMENT ==="
$venvDir = Join-Path $RepoRoot ".venv"
if (-not (Test-Path $venvDir)) {
    Write-Host "Creating Python virtual environment in .venv..."
    python -m venv $venvDir
}
$venvPip = Join-Path $venvDir "Scripts\pip.exe"
& $venvPip install -r (Join-Path $RepoRoot "requirements.txt") --quiet

Write-Host "=== 3. CONFIGURATION MANAGEMENT ==="
$confFile = Join-Path $neo4jHome "conf\neo4j.conf"
$overridesFile = Join-Path $RepoRoot "config\neo4j.overrides.conf"

if (Test-Path $confFile) {
    $existingConf = Get-Content $confFile -Raw
    $managedBlock = Get-Content $overridesFile -Raw
    
    # Strip any previous managed block and BOM
    $cleanConf = $existingConf -replace "(?s)# >>> customer-360 managed block.*# <<< customer-360 managed block <<<`r?\n?", ""
    $cleanConf = $cleanConf.TrimStart([char]65279)
    $finalConf = $cleanConf.TrimEnd() + "`r`n`r`n" + $managedBlock.Trim() + "`r`n"
    
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($confFile, $finalConf, $utf8NoBom)
    Write-Host "Merged managed configuration block into $confFile"
}

Write-Host "=== 4. INITIAL PASSWORD SETUP ==="
$dbDataDir = Join-Path $neo4jHome "data\databases\neo4j"
if (-not (Test-Path $dbDataDir)) {
    $adminBat = Join-Path $neo4jHome "bin\neo4j-admin.bat"
    $pass = $envVars["NEO4J_PASSWORD"]
    Write-Host "Setting initial Neo4j admin password..."
    & $adminBat dbms set-initial-password $pass
} else {
    Write-Host "Database directory exists; skipping set-initial-password."
}

Write-Host "=== 5. SERVICE REGISTRATION & STARTUP ==="
$serviceName = if ($envVars.ContainsKey("NEO4J_SERVICE_NAME")) { $envVars["NEO4J_SERVICE_NAME"] } else { "neo4j" }
$neo4jBat = Join-Path $neo4jHome "bin\neo4j.bat"

if ($isAdmin) {
    $svc = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if (-not $svc) {
        Write-Host "Installing Windows Service '$serviceName'..."
        & $neo4jBat windows-service install
    }
    $isManual = $PSBoundParameters.ContainsKey('ManualStartup') -and $ManualStartup
    $startupType = if ($isManual) { "Manual" } else { "Automatic" }
    Set-Service -Name $serviceName -StartupType $startupType
    Start-Service -Name $serviceName
} else {
    $svc = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
    if ($svc) {
        Write-Host "Starting Windows service '$serviceName'..."
        Start-Service -Name $serviceName
    } else {
        Write-Host "Launching Neo4j server process..."
        Start-Process -FilePath $neo4jBat -ArgumentList "console" -WindowStyle Hidden
    }
}

Write-Host "=== 6. WAITING FOR BOLT (7687) ==="
if (-not (Wait-Port -Address "127.0.0.1" -Port 7687 -TimeoutSeconds 60)) {
    Write-Error "Neo4j service failed to respond on port 7687 within 60 seconds."
    exit 1
}

Write-Host "=== 7. SEEDING DATABASE ==="
powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "seed.ps1")

Write-Host "`n=========================================="
Write-Host " Neo4j Customer 360 Setup Complete! "
Write-Host " Browser: http://localhost:7474"
Write-Host " Bolt:    bolt://localhost:7687"
Write-Host " Service: $serviceName (State: Running)"
Write-Host "=========================================="
