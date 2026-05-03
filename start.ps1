param(
    [switch]$Headless = $false,
    [switch]$Automated = $false
)

if ($Headless -and ($Host.UI.RawUI.WindowTitle -notmatch "Hidden")) {
    Start-Process pwsh -ArgumentList "-NoProfile", "-File", $PSCommandPath, "-Headless" -WindowStyle Hidden
    exit
}

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSCommandPath
$WindowStyle = if ($Headless) { "Hidden" } else { "Normal" }

$BackendPort = 10951
$FrontendPort = 10950
$OpencodePort = 4096

Write-Host " [opencode-cli-mcp] Starting..." -ForegroundColor White -BackgroundColor Cyan
Write-Host ""

function Clear-Port($Port) {
    $procs = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    foreach ($p in $procs) {
        Write-Host "  Killing PID $($p.OwningProcess) on port $Port" -ForegroundColor Yellow
        try { Stop-Process -Id $p.OwningProcess -Force } catch {}
    }
}

function Wait-For-TCP($Port, $TimeoutSeconds = 60) {
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    while ($timer.Elapsed.TotalSeconds -lt $TimeoutSeconds) {
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $tcp.Connect("127.0.0.1", $Port)
            $tcp.Close()
            return $true
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    Write-Error "Backend failed to bind port $Port within ${TimeoutSeconds}s"
    exit 1
}

Write-Host " Clearing zombie ports..." -ForegroundColor Yellow
Clear-Port $BackendPort
Clear-Port $FrontendPort
Clear-Port $OpencodePort

$env:OPENCODE_SERVE_URL = "http://127.0.0.1:$OpencodePort"

Write-Host " Starting opencode serve..." -ForegroundColor Yellow
$opencodeJob = Start-Job -ScriptBlock {
    param($port)
    opencode serve --port $port
} -ArgumentList $OpencodePort

Start-Sleep -Seconds 2

Write-Host " Starting API backend on port $BackendPort..." -ForegroundColor Yellow
$backendJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    uv run python -m api.main
} -ArgumentList $RepoRoot

Wait-For-TCP -Port $BackendPort -TimeoutSeconds 90
Write-Host " Backend ready on port $BackendPort" -ForegroundColor Green

Start-Sleep -Seconds 1

if ($Headless) {
    Write-Host " Starting frontend headlessly..." -ForegroundColor Yellow
    $frontendJob = Start-Job -ScriptBlock {
        param($dir)
        Set-Location "$dir\web_sota"
        npm run dev
    } -ArgumentList $RepoRoot
    Write-Host " [SOTA] opencode-cli-mcp started headlessly." -ForegroundColor Cyan
} else {
    Write-Host " Starting frontend on port $FrontendPort..." -ForegroundColor Yellow
    $frontendJob = Start-Job -ScriptBlock {
        param($dir)
        Set-Location "$dir\web_sota"
        npm run dev
    } -ArgumentList $RepoRoot
}

Write-Host ""
Write-Host " [opencode-cli-mcp] All services starting:" -ForegroundColor Green
Write-Host "   Frontend : http://localhost:$FrontendPort" -ForegroundColor Cyan
Write-Host "   Backend  : http://localhost:$BackendPort" -ForegroundColor Cyan
Write-Host "   API Docs : http://localhost:$BackendPort/docs" -ForegroundColor Cyan
Write-Host "   opencode : http://localhost:$OpencodePort" -ForegroundColor Cyan
Write-Host ""

if ($Automated -or !$Headless) {
    Start-Process "http://localhost:$FrontendPort"
}

try {
    while ($true) { Start-Sleep -Seconds 10 }
} finally {
    $opencodeJob | Stop-Job -ErrorAction SilentlyContinue | Remove-Job -ErrorAction SilentlyContinue
    $backendJob | Stop-Job -ErrorAction SilentlyContinue | Remove-Job -ErrorAction SilentlyContinue
    $frontendJob | Stop-Job -ErrorAction SilentlyContinue | Remove-Job -ErrorAction SilentlyContinue
}
