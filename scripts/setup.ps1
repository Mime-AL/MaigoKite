[CmdletBinding()]
param([ValidateSet('all', 'dev', 'python', 'electron')][string]$Target = 'all')
$ErrorActionPreference = 'Stop'
Get-Command node -ErrorAction Stop | Out-Null
& node (Join-Path $PSScriptRoot 'local.cjs') setup $Target
exit $LASTEXITCODE
