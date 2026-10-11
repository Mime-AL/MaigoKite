[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Get-Command node -ErrorAction Stop | Out-Null
& node (Join-Path $PSScriptRoot 'local.cjs') setup
exit $LASTEXITCODE
