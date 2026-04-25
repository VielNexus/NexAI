<# 
start-agentx.ps1
Launch AgentX stack: API backend + Desktop (Tauri) + AgentXWeb (Vite) + optional tests.

Usage:
  powershell -ExecutionPolicy Bypass -File .\start-agentx.ps1
  powershell -ExecutionPolicy Bypass -File .\start-agentx.ps1 -RunTests
  powershell -ExecutionPolicy Bypass -File .\start-agentx.ps1 -RunTests -NoDesktop
#>

param(
  [string]$RepoRoot = $PSScriptRoot,
  [switch]$RunTests,
  [switch]$NoApi,
  [switch]$NoDesktop,
  [switch]$NoWeb,
  [switch]$NoAgentXTests
)

function Get-ApiPythonCommand {
  param(
    [Parameter(Mandatory=$true)][string]$RepoRoot
  )

  $apiDir = Join-Path $RepoRoot "apps\api"
  $venvPython = Join-Path $apiDir ".venv\Scripts\python.exe"

  if (Test-Path $venvPython) {
    return "& '$venvPython' -m agentx_api"
  }

  return "python -m agentx_api"
}

function New-RunnerWindow {
  param(
    [Parameter(Mandatory=$true)][string]$Title,
    [Parameter(Mandatory=$true)][string]$WorkDir,
    [Parameter(Mandatory=$true)][string]$Command
  )

  if (-not (Test-Path $WorkDir)) {
    Write-Host "Skipping $Title (missing dir): $WorkDir" -ForegroundColor Yellow
    return
  }

  $ps = @"
`$Host.UI.RawUI.WindowTitle = '$Title'
Set-Location -LiteralPath '$WorkDir'
Write-Host '[$Title] Working dir: ' (Get-Location) -ForegroundColor Cyan
Write-Host '[$Title] Command: $Command' -ForegroundColor Cyan
$Command
"@

  Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy", "Bypass",
    "-Command", $ps
  ) | Out-Null
}

Write-Host "RepoRoot: $RepoRoot" -ForegroundColor Green
if (-not (Test-Path $RepoRoot)) {
  throw "Repo root not found: $RepoRoot"
}

# Optional tests (run in their own window so they don't block launch)
if ($RunTests) {
  New-RunnerWindow -Title "AgentX Tests (Repo Root)" -WorkDir $RepoRoot -Command "python -m pytest -q"
  if (-not $NoAgentXTests) {
    New-RunnerWindow -Title "AgentX Tests" -WorkDir (Join-Path $RepoRoot "AgentX") -Command "python -m pytest -q"
  }
}

# API backend
if (-not $NoApi) {
  $apiCommand = Get-ApiPythonCommand -RepoRoot $RepoRoot
  New-RunnerWindow -Title "AgentX API Backend" -WorkDir (Join-Path $RepoRoot "apps\api") -Command $apiCommand
}

# Desktop (Tauri)
#if (-not $NoDesktop) {
#  New-RunnerWindow -Title "AgentX Desktop (Tauri Dev)" -WorkDir (Join-Path $RepoRoot "apps\desktop") -Command "npm exec tauri dev"
#}

# AgentXWeb (Vite)
if (-not $NoWeb) {
  New-RunnerWindow -Title "AgentXWeb (Dev)" -WorkDir (Join-Path $RepoRoot "AgentXWeb") -Command "npm run dev"
}

Write-Host "`nLaunched requested services. Close any window to stop that service." -ForegroundColor Green
Write-Host "Tip: re-run with -RunTests to open test windows." -ForegroundColor DarkGray
