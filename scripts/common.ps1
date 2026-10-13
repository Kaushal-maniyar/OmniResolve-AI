Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

function Get-DotEnv {
    $envFile = Join-Path $RepoRoot ".env"
    $envVars = @{}
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            $line = $_.Trim()
            if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
                $parts = $line.Split("=", 2)
                $key = $parts[0].Trim()
                $val = $parts[1].Trim().Trim('"').Trim("'")
                $envVars[$key] = $val
            }
        }
    }
    return $envVars
}

function Get-Neo4jVersionPin {
    $verFile = Join-Path $RepoRoot "neo4j.version"
    $res = @{}
    if (Test-Path $verFile) {
        Get-Content $verFile | ForEach-Object {
            $line = $_.Trim()
            if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
                $parts = $line.Split("=", 2)
                $res[$parts[0].Trim()] = $parts[1].Trim()
            }
        }
    }
    return $res
}

function Get-Neo4jHome {
    $envVars = Get-DotEnv
    if ($envVars.ContainsKey("NEO4J_HOME") -and $envVars["NEO4J_HOME"]) {
        return $envVars["NEO4J_HOME"]
    }
    if ($env:NEO4J_HOME) {
        return $env:NEO4J_HOME
    }
    $pin = Get-Neo4jVersionPin
    $ver = $pin["NEO4J_VERSION"]
    return "C:\neo4j\neo4j-community-$ver"
}

function Assert-Admin {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    $isAdmin = $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Host "Notice: Running in non-elevated user mode. Service registration may require elevation."
    }
    return $isAdmin
}

function Ensure-JavaOnPath {
    if (Get-Command java -ErrorAction SilentlyContinue) { return }
    # Search common JDK 21 installation locations
    $candidatePaths = @(
        "C:\Program Files\Eclipse Adoptium\jdk-21*\bin",
        "C:\Program Files\Java\jdk-21*\bin",
        "C:\Program Files\Microsoft\jdk-21*\bin"
    )
    foreach ($pat in $candidatePaths) {
        $found = Get-Item -Path $pat -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) {
            $binDir = $found.FullName
            $jdkHome = Resolve-Path (Join-Path $binDir "..")
            $env:JAVA_HOME = $jdkHome.Path
            $env:Path = "$binDir;" + $env:Path
            Write-Host "Auto-configured JAVA_HOME=$env:JAVA_HOME"
            return
        }
    }
}

function Assert-Java {
    Ensure-JavaOnPath
    $pin = Get-Neo4jVersionPin
    $reqMajor = [int]($pin["REQUIRED_JAVA_MAJOR"])
    
    if (-not (Get-Command java -ErrorAction SilentlyContinue)) {
        Write-Error "Java executable not found! JDK $reqMajor is required."
        exit 1
    }
    
    $verOutput = (cmd /c "java -version 2>&1") | Out-String
    if ($verOutput -match 'version "(\d+)') {
        $major = [int]$matches[1]
        if ($major -lt $reqMajor) {
            Write-Error "Java version $major detected, but JDK $reqMajor+ is required."
            exit 1
        }
        Write-Host "Java JDK $major verified successfully."
    }
}

function Wait-Port {
    param(
        [string]$Address = "127.0.0.1",
        [int]$Port = 7687,
        [int]$TimeoutSeconds = 60
    )
    $startTime = Get-Date
    while (((Get-Date) - $startTime).TotalSeconds -lt $TimeoutSeconds) {
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $asyncResult = $tcp.BeginConnect($Address, $Port, $null, $null)
            $wait = $asyncResult.AsyncWaitHandle.WaitOne(1000, $false)
            if ($wait -and $tcp.Connected) {
                $tcp.Close()
                return $true
            }
            $tcp.Close()
        } catch {}
        Start-Sleep -Seconds 1
    }
    return $false
}

function Invoke-Python {
    param([string[]]$Arguments)
    Ensure-JavaOnPath
    $venvPy = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    $pyCmd = if (Test-Path $venvPy) { $venvPy } else { "python" }
    
    $envVars = Get-DotEnv
    foreach ($k in $envVars.Keys) {
        [System.Environment]::SetEnvironmentVariable($k, $envVars[$k], "Process")
    }
    
    $env:PYTHONPATH = (Join-Path $RepoRoot "src") + ";" + $env:PYTHONPATH
    & $pyCmd $Arguments
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Python execution failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}
