# SOTA MCPB pack - fresh-stage pipeline (MCPB_PACKAGING_STANDARDS.md sec 2.5)
# 1. Wipe mcpb/src, copy repo src/<pkg> -> mcpb/src/<pkg> (never flatten)
# 2. Sync mcpb manifest/README/CHANGELOG/assets from the live repo
# 3. Mechanical gates: 3-4-100 prompts, no pycache/bak under mcpb, entry import resolves
# 4. mcpb pack mcpb/ -> dist/{name}-v{ver}.mcpb
param([string]$RepoRoot = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

$proj = Get-Content pyproject.toml -Raw
$name = if ($proj -match '(?m)^name = "(.*)"') { $matches[1] } else { Split-Path -Leaf $PWD }
$ver = if ($proj -match '(?m)^version = "(.*)"') { $matches[1] } else { "0.1.0" }
$pkg = $name -replace '-', '_'
$stageRoot = Join-Path $RepoRoot "mcpb"
$stageSrc = Join-Path $stageRoot "src"

Write-Host "=== MCPB pack: $name v$ver ===" -ForegroundColor Cyan

# Step 0: fresh stage - wipe + recopy src/<pkg> (preserve package dir)
if (-not (Test-Path (Join-Path $RepoRoot "src\$pkg"))) {
    throw "src\$pkg not found - nothing to stage"
}
if (Test-Path $stageSrc) {
    Write-Host "  Wiping stale mcpb/src..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $stageSrc
}
New-Item -ItemType Directory -Force -Path $stageSrc | Out-Null
Copy-Item -Recurse -Force (Join-Path $RepoRoot "src\$pkg") (Join-Path $stageSrc $pkg)
Write-Host "  Staged src\$pkg -> mcpb\src\$pkg (fresh copy)" -ForegroundColor Green

# Step 1: sync docs + assets (manifest.json lives at the stage root already)
if (Test-Path (Join-Path $RepoRoot ".mcpbignore")) { Copy-Item -Force (Join-Path $RepoRoot ".mcpbignore") $stageRoot }
if (Test-Path (Join-Path $RepoRoot "README.md")) { Copy-Item -Force (Join-Path $RepoRoot "README.md") $stageRoot }
if (Test-Path (Join-Path $RepoRoot "CHANGELOG.md")) { Copy-Item -Force (Join-Path $RepoRoot "CHANGELOG.md") $stageRoot }
New-Item -ItemType Directory -Force -Path (Join-Path $stageRoot "assets\prompts") | Out-Null
Copy-Item -Force (Join-Path $RepoRoot "assets\icon.png") (Join-Path $stageRoot "assets\icon.png")
Copy-Item -Force (Join-Path $RepoRoot "assets\prompts\system.md") (Join-Path $stageRoot "assets\prompts\system.md")
Copy-Item -Force (Join-Path $RepoRoot "assets\prompts\user.md") (Join-Path $stageRoot "assets\prompts\user.md")
Copy-Item -Force (Join-Path $RepoRoot "assets\prompts\examples.json") (Join-Path $stageRoot "assets\prompts\examples.json")
Write-Host "  Synced manifest, README, CHANGELOG, assets" -ForegroundColor Green

# Step 2: gates
function Word-Count([string]$Path) {
  (@(Get-Content -Raw $Path) -split '\s+' | Where-Object { $_ }).Count
}
$sys = Word-Count (Join-Path $stageRoot "assets\prompts\system.md")
$user = Word-Count (Join-Path $stageRoot "assets\prompts\user.md")
$ex = (Get-Content (Join-Path $stageRoot "assets\prompts\examples.json") -Raw | ConvertFrom-Json).Count
if ($sys -lt 3000 -or $user -lt 4000 -or $ex -lt 100) {
    throw "3-4-100 FAIL: system=$sys user=$user examples=$ex (need 3000 / 4000 / 100)"
}
Write-Host "  Prompts 3-4-100 OK (system=$sys user=$user examples=$ex)" -ForegroundColor Green

$pycache = Get-ChildItem $stageRoot -Recurse -Include "*.pyc", "*.bak", "*.bak.*", "*.orig" -ErrorAction SilentlyContinue
$pycDirs = Get-ChildItem $stageRoot -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue
if ($pycache -or $pycDirs) {
    throw "Pollution under mcpb/: pycache/bak files found - refusing to pack"
}

# Entry-point import resolves from mcpb/src alone (not site-packages)
$importCheck = & uv run python -c "import sys; sys.path.insert(0, r'$stageSrc'); import $pkg.server; print($pkg.server.__file__)" 2>&1
if ($LASTEXITCODE -ne 0 -or $importCheck -notmatch [regex]::Escape($stageSrc)) {
    throw "Entry-point import failed or resolved outside mcpb/src: $importCheck"
}
Write-Host "  Entry import OK: $importCheck" -ForegroundColor Green

# Step 3: pack
New-Item -ItemType Directory -Force -Path (Join-Path $RepoRoot "dist") | Out-Null
$out = Join-Path $RepoRoot "dist\$name-v$ver.mcpb"
npx --yes @anthropic-ai/mcpb pack $stageRoot $out
if ($LASTEXITCODE -ne 0) { throw "mcpb pack failed" }
$sizeMB = [math]::Round((Get-Item $out).Length / 1MB, 2)
Write-Host "Bundle: $out ($sizeMB MB)" -ForegroundColor Green

# Step 4: clean the staged source so the next run cannot reuse it stale
Remove-Item -Recurse -Force $stageSrc
Write-Host "  Cleaned mcpb/src" -ForegroundColor Yellow
