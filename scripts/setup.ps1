[CmdletBinding()]
param([ValidateSet('all', 'electron')][string]$Target = 'all')
$ErrorActionPreference = 'Stop'
Get-Command node -ErrorAction Stop | Out-Null
& node (Join-Path $PSScriptRoot 'local.cjs') setup $Target
exit $LASTEXITCODE
