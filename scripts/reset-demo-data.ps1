param(
    [switch]$Confirm
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot "common.ps1")

$isConfirmed = $PSBoundParameters.ContainsKey('Confirm') -and $Confirm

if (-not $isConfirmed) {
    $title = "Reset Demo Data"
    $message = "Are you sure you want to delete all demo nodes and relationships? Constraints and schema will remain."
    $yes = New-Object System.Management.Automation.Host.ChoiceDescription "&Yes", "Proceeds with reset."
    $no = New-Object System.Management.Automation.Host.ChoiceDescription "&No", "Cancels reset."
    $options = [System.Management.Automation.Host.ChoiceDescription[]]($yes, $no)
    $result = $host.ui.PromptForChoice($title, $message, $options, 1)
    if ($result -ne 0) {
        Write-Host "Reset cancelled."
        exit 0
    }
}

Invoke-Python @("-m", "c360.graph.reset")
