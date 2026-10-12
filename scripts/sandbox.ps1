[CmdletBinding()]
param(
    [ValidateSet('status', 'install', 'uninstall')][string]$Action = 'status',
    [switch]$ConfirmSystemChanges
)
$ErrorActionPreference = 'Stop'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'This entry point requires native Windows.'
}
Get-Command node -ErrorAction Stop | Out-Null
if ($Action -ne 'status') {
    Write-Warning 'SRT is alpha and shares a machine-wide sandbox account with other SRT clients. Stop MaigoKite and those clients first.'
    Write-Warning 'Install changes local accounts, registry, ACLs and WFP rules with UAC. Uninstall removes the shared sandbox account and its profile. No TLS interception CA is requested.'
    if (-not $ConfirmSystemChanges) {
        throw 'Read docs/user-guide/Configuration.md, then explicitly pass -ConfirmSystemChanges to proceed.'
    }
    if (Get-NetTCPConnection -State Listen -LocalPort 8080 -ErrorAction SilentlyContinue) {
        throw 'Port 8080 is active. Stop the running suite before changing the sandbox installation.'
    }
}
$Bridge = Join-Path $PSScriptRoot 'windows-sandbox/bridge.mjs'
if ($Action -eq 'status') {
    & node $Bridge status
} else {
    & node $Bridge $Action --confirm-system-changes
}
exit $LASTEXITCODE
