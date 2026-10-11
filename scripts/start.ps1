[CmdletBinding()]
param(
    [ValidateSet('web', 'desktop')][string]$Target = 'web',
    [ValidateSet('dev', 'built')][string]$Mode = 'dev'
)
$ErrorActionPreference = 'Stop'
Get-Command node -ErrorAction Stop | Out-Null
& node (Join-Path $PSScriptRoot 'local.cjs') start $Target $Mode
exit $LASTEXITCODE
