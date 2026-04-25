<#
start-sol.ps1
Deprecated compatibility wrapper for start-agentx.ps1.
#>

param(
  [string]$RepoRoot = $PSScriptRoot,
  [switch]$RunTests,
  [switch]$NoApi,
  [switch]$NoDesktop,
  [switch]$NoWeb,
  [switch]$NoAgentxTests
)

Write-Warning "start-sol.ps1 is deprecated; use start-agentx.ps1."
$script = Join-Path $PSScriptRoot "start-agentx.ps1"
& $script -RepoRoot $RepoRoot -RunTests:$RunTests -NoApi:$NoApi -NoDesktop:$NoDesktop -NoWeb:$NoWeb -NoAgentxTests:$NoAgentxTests
exit $LASTEXITCODE
