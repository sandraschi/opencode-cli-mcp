param(
    [switch]$Headless = $false,
    [switch]$Automated = $false,
    [switch]$BackendOnly
)

if ($Headless -and ($Host.UI.RawUI.WindowTitle -notmatch "Hidden")) {
    Start-Process pwsh -ArgumentList "-NoProfile", "-File", $PSCommandPath, "-Headless" -WindowStyle Hidden
    exit
}

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSCommandPath
$BackendPort = 10951
$FrontendPort = 10950
$OpencodePort = 4096

$FleetStartPath = Join-Path $RepoRoot "scripts\FleetStartMode.ps1"
if (-not (Test-Path -LiteralPath $FleetStartPath)) {
    Write-Host "ERROR: Missing vendored launcher helper: $FleetStartPath" -ForegroundColor Red
    exit 1
}
. $FleetStartPath
Stop-FleetPortSquatters -Ports @($BackendPort, $FrontendPort, $OpencodePort) -Label "opencode-cli-mcp"

if (-not (Assert-FleetPortsAvailable -Ports @($BackendPort, $FrontendPort, $OpencodePort) -Label "opencode-cli-mcp")) { exit 1 }

Write-Host " [opencode-cli-mcp] Starting..." -ForegroundColor White -BackgroundColor Cyan

$env:OPENCODE_SERVE_URL = "http://127.0.0.1:${OpencodePort}"

Write-Host " Starting opencode serve..." -ForegroundColor Yellow
$opencodeCmd = "opencode serve --port $OpencodePort"
Start-Process powershell -ArgumentList "-NoProfile", "-WindowStyle", "Normal", "-Command", $opencodeCmd

Start-Sleep -Seconds 2

Write-Host " Starting API backend on port $BackendPort..." -ForegroundColor Yellow
$backendCmd = "Set-Location '$RepoRoot'; uv run --project '$RepoRoot' python -m api.main"
Start-Process powershell -ArgumentList "-NoProfile", "-WindowStyle", "Normal", "-Command", $backendCmd

$healthUrl = "http://127.0.0.1:$BackendPort/api/v1/health"
$ready = $false
for ($i = 0; $i -lt 90; $i++) {
    try {
        $r = Invoke-WebRequest -Uri $healthUrl -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep -Milliseconds 500
}
if (-not $ready) {
    Write-Error "Backend failed to respond at $healthUrl within 90s"
    exit 1
}
Write-Host " Backend ready on port $BackendPort" -ForegroundColor Green

if ($BackendOnly) {
    while ($true) { Start-Sleep -Seconds 60 }
}

$WebRoot = Join-Path $RepoRoot "web_sota"
if (-not (Test-Path (Join-Path $WebRoot "node_modules"))) {
    Set-Location $WebRoot
    npm install
}

if ($Automated -or (-not $Headless)) {
    Start-Process "http://localhost:${FrontendPort}"
}

Write-Host " Starting frontend on port $FrontendPort..." -ForegroundColor Yellow
Set-Location $WebRoot
$env:PORT = "$FrontendPort"
npm run dev -- --host --port $FrontendPort


