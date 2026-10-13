param(
    [string]$ZipPath = (Join-Path $PSScriptRoot "..\downloads\neo4j-community-5.26.0-windows.zip")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot "common.ps1")

if (-not (Test-Path $ZipPath)) {
    Write-Error "ZIP archive not found at $ZipPath"
    exit 1
}

$pin = Get-Neo4jVersionPin
$expectedHash = $pin["NEO4J_ZIP_SHA256"]

Write-Host "Verifying SHA-256 checksum for $ZipPath..."
$actualHash = (Get-FileHash $ZipPath -Algorithm SHA256).Hash

if ($actualHash.ToUpper() -ne $expectedHash.ToUpper()) {
    Write-Error "Hash mismatch!`nExpected: $expectedHash`nActual:   $actualHash"
    exit 1
}
Write-Host "SHA-256 hash verified successfully: $actualHash"

$neo4jHome = Get-Neo4jHome
$parentDir = Split-Path $neo4jHome -Parent

if (Test-Path $neo4jHome) {
    Write-Host "Neo4j installation directory already exists at $neo4jHome. Skipping extraction."
    exit 0
}

if (-not (Test-Path $parentDir)) {
    New-Item -ItemType Directory -Force -Path $parentDir | Out-Null
}

Write-Host "Extracting Neo4j ZIP to $parentDir..."
Expand-Archive -Path $ZipPath -DestinationPath $parentDir -Force

# Rename extracted folder if needed
$extractedName = "neo4j-community-" + $pin["NEO4J_VERSION"]
$extractedPath = Join-Path $parentDir $extractedName

if ((Test-Path $extractedPath) -and ($extractedPath -ne $neo4jHome)) {
    Move-Item -Path $extractedPath -Destination $neo4jHome -Force
}

$binBat = Join-Path $neo4jHome "bin\neo4j.bat"
if (-not (Test-Path $binBat)) {
    Write-Error "Installation failed: $binBat not found after extraction."
    exit 1
}

Write-Host "Neo4j installed successfully at $neo4jHome"
