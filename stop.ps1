$ProjectRoot = $PSScriptRoot

$FleetStartPath = Join-Path $ProjectRoot "scripts\FleetStartMode.ps1"
if (-not (Test-Path -LiteralPath $FleetStartPath)) {
    Write-Host "ERROR: Missing vendored launcher helper: $FleetStartPath" -ForegroundColor Red
    exit 1
}
. $FleetStartPath

if (-not (Stop-FleetPortListeners -Ports @(10951, 10950, 4096) -Label "opencode-cli-mcp")) { exit 1 }
