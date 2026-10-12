[CmdletBinding()]
param([ValidateSet('web', 'desktop', 'all', 'python', 'vue')][string]$Target = 'all')
$ErrorActionPreference = 'Stop'
Get-Command node -ErrorAction Stop | Out-Null
& node (Join-Path $PSScriptRoot 'local.cjs') build $Target
exit $LASTEXITCODE
