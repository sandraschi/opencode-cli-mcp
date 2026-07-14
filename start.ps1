param(
    [switch]$Headless = $false,
    [switch]$Automated = $false,
    [switch]$BackendOnly,
    [switch]$ReuseIfRunning)

if ($Headless -and ($Host.UI.RawUI.WindowTitle -notmatch "Hidden")) {
    Start-Process powershell -ArgumentList "-NoProfile", "-File", $PSCommandPath, "-Headless" -WindowStyle Hidden
    exit
}

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSCommandPath
$BackendPort = 10951
$FrontendPort = 10950
$OpencodePort = 4096

# NAKED_PC_INSTALL_STANDARD: fail early with actionable hints, not stack traces.
function Require-Command {
    param([string]$Name, [string]$Hint)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: '$Name' not found on PATH. $Hint" -ForegroundColor Red
        exit 1
    }
}
Require-Command uv "Install: winget install astral-sh.uv"
Require-Command bun "Install: powershell -c `"irm bun.sh/install.ps1 | iex`""
Require-Command opencode "Install: see https://opencode.ai (or bun add -g opencode-ai)"

$FleetStartPath = Join-Path $RepoRoot "scripts\FleetStartMode.ps1"
if (-not (Test-Path -LiteralPath $FleetStartPath)) {
    Write-Host "ERROR: Missing vendored launcher helper: $FleetStartPath" -ForegroundColor Red
    exit 1
}
. $FleetStartPath

$portResolve = @{
    Ports      = @($BackendPort, $FrontendPort, $OpencodePort)
    Label      = "opencode-cli-mcp"
    AllowReuse = $ReuseIfRunning
}
if ($ReuseIfRunning) {
    $portResolve.HealthChecks = @{
        $BackendPort = "http://127.0.0.1:$BackendPort/api/v1/health"
        $FrontendPort = "http://127.0.0.1:$FrontendPort/"
        $OpencodePort = "http://127.0.0.1:$OpencodePort/api/v1/health"
    }
}
$portState = Resolve-FleetPortConflict @portResolve
if ($portState.Action -eq 'Blocked') { exit 1 }
if ($portState.Reuse) { return }


Write-Host " [opencode-cli-mcp] Starting..." -ForegroundColor White -BackgroundColor Cyan

$env:OPENCODE_SERVE_URL = "http://127.0.0.1:${OpencodePort}"

Write-Host " Starting opencode serve..." -ForegroundColor Yellow
$opencodeCmd = "opencode serve --port $OpencodePort"
Start-Process powershell -ArgumentList "-NoProfile", "-WindowStyle", "Normal", "-Command", $opencodeCmd

Start-Sleep -Seconds 2

Write-Host " Syncing Python deps (uv sync)..." -ForegroundColor Yellow
Push-Location $RepoRoot
try { uv sync; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } } finally { Pop-Location }

Write-Host " Starting API backend on port $BackendPort..." -ForegroundColor Yellow
$backendCmd = "Set-Location '$RepoRoot'; uv run --project '$RepoRoot' python -m api.main"
Start-Process powershell -ArgumentList "-NoProfile", "-WindowStyle", "Normal", "-Command", $backendCmd

$healthUrl = "http://127.0.0.1:$BackendPort/api/v1/health"
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $r = Invoke-WebRequest -Uri $healthUrl -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep -Milliseconds 500
}
if (-not $ready) {
    Write-Error "Backend failed to respond at $healthUrl within 30s"
    exit 1
}
Write-Host " Backend ready on port $BackendPort" -ForegroundColor Green

if ($BackendOnly) {
    while ($true) { Start-Sleep -Seconds 60 }
}

$WebRoot = Join-Path $RepoRoot "web_sota"
if (-not (Test-Path (Join-Path $WebRoot "node_modules"))) {
    Set-Location $WebRoot
    bun install
}

if ($Automated -or (-not $Headless)) {
    Start-Process "http://localhost:${FrontendPort}"
}

Write-Host " Starting frontend on port $FrontendPort..." -ForegroundColor Yellow
Set-Location $WebRoot
$env:PORT = "$FrontendPort"
bun run dev -- --host --port $FrontendPort


