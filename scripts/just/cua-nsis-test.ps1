# Run CUA-NSIS smoke test (install -> launch -> nav walk -> uninstall)
# Self-contained: resolves repo root from its own location (scripts/just/.. = repo root).
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $repoRoot
if (Test-Path ".venv\Scripts\python.exe") {
    & ".venv\Scripts\python.exe" scripts/cua-smoke.py
} else {
    & py scripts/cua-smoke.py
}
exit $LASTEXITCODE

# Sync detailed report to reports and mcd if exists
$date = Get-Date -Format 'yyyy-MM-dd'; $repo = Split-Path -Leaf $repoRoot; $md = Join-Path $repoRoot "reports/cua-$repo-$date.md"; if (Test-Path $md) { Copy-Item $md "D:/Dev/repos/mcp-central-docs/reports/" -Force; Write-Host "Synced $md to mcd" }
