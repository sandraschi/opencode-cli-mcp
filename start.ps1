param(
    [switch]$Automated = $false
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSCommandPath

$BackendPort = 10951
$FrontendPort = 10950
$OpencodePort = 4096

Write-Host " [opencode-cli-mcp] Starting..." -ForegroundColor White -BackgroundColor Cyan
Write-Host ""

function Clear-Port($Port) {
    $procs = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    foreach ($p in $procs) {
        try { Stop-Process -Id $p.OwningProcess -Force } catch {}
    }
}

Write-Host " Clearing ports..." -ForegroundColor Yellow
Clear-Port $BackendPort
Clear-Port $FrontendPort
Clear-Port $OpencodePort

Write-Host " Starting opencode serve..." -ForegroundColor Yellow
$opencodeJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    opencode serve --port 4096
} -ArgumentList $RepoRoot

Start-Sleep -Seconds 2

Write-Host " Starting API backend on port $BackendPort..." -ForegroundColor Yellow
$backendJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    uv run python -m api.main
} -ArgumentList $RepoRoot

Start-Sleep -Seconds 3

Write-Host " Starting frontend on port $FrontendPort..." -ForegroundColor Yellow
$frontendJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location "$dir\web_sota"
    npm run dev
} -ArgumentList $RepoRoot

Write-Host ""
Write-Host " [opencode-cli-mcp] All services starting:" -ForegroundColor Green
Write-Host "   Frontend : http://localhost:$FrontendPort" -ForegroundColor Cyan
Write-Host "   Backend  : http://localhost:$BackendPort" -ForegroundColor Cyan
Write-Host "   API Docs : http://localhost:$BackendPort/docs" -ForegroundColor Cyan
Write-Host "   opencode : http://localhost:$OpencodePort" -ForegroundColor Cyan
Write-Host ""
Write-Host " Press Ctrl+C to stop all services" -ForegroundColor Gray

if ($Automated) {
    Start-Process "http://localhost:$FrontendPort"
}

try {
    while ($true) { Start-Sleep -Seconds 10 }
} finally {
    $opencodeJob | Stop-Job | Remove-Job
    $backendJob | Stop-Job | Remove-Job
    $frontendJob | Stop-Job | Remove-Job
}
