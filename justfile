set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]

import 'scripts/just/fleet.just'

NAME := "opencode-cli-mcp"
DESC := "MCP server wrapping opencode CLI"
VER := "0.2.3"

# Dedicated opencode serve port for this server (NOT 4096 - the official
# OpenCode desktop app owns 4096 with a per-session password). Exported so
# every recipe (serve/api/start) talks to our own serve on 4097.
export OPENCODE_SERVE_URL := "http://127.0.0.1:4097"

# Open the interactive recipe dashboard in the browser
default:
    @just --list

# ── Development ─────────────────────────────────────────
# Install dependencies
install:
    uv sync
    cd web_sota && npm install

# Run the MCP server (stdio)
serve:
    uv run python -m opencode_cli_mcp.server

# Run the API backend
api:
    uv run python -m api.main

# Run the webapp frontend
web:
    cd web_sota; npm run dev

# Start everything via start.ps1
start:
    powershell -ExecutionPolicy Bypass -File start.ps1

# Start headless (for fleet/production)
start-headless:
    powershell -ExecutionPolicy Bypass -File start.ps1 -Headless

# ── Fleet ──────────────────────────────────────────────
# Fleet health check (probe our own ports)
fleet-health:
    powershell -NoLogo -Command " \
        $ports = @(10950, 10951); \
        foreach ($p in $ports) { \
            try { \
                $t = [System.Net.Sockets.TcpClient]::new(); \
                $t.Connect('127.0.0.1', $p); \
                $t.Close(); \
                Write-Host \"  Port $p : OK\" -ForegroundColor Green; \
            } catch { \
                Write-Host \"  Port $p : DOWN\" -ForegroundColor Red; \
            } \
        }"

# ── Quality ─────────────────────────────────────────────
# Run lint + format check
check:
    uv run ruff check .
    uv run ruff format --check .

# Auto-format
format:
    uv run ruff format .

# Run tests
test:
    uv run pytest tests/ -v

# Run Playwright e2e tests (webapp)
e2e:
    cd web_sota; npx playwright test

# Run type checker
type-check:
    uv run pyright

# Run every gate: ruff, pytest, pyright, tsc, biome - abort on first failure
certify:
    uv run ruff check .
    uv run pytest tests/ -q
    uv run pyright src/ api/
    cd web_sota; npx tsc --noEmit
    cd web_sota; npm run biome:ci
    Write-Host "=== CERTIFY PASSED - all gates green ===" -ForegroundColor Green

# ── Build ───────────────────────────────────────────────
# Build webapp
build-web:
    cd web_sota; npm run build

# ── Native (Tauri) ──────────────────────────────────────────────────────────

# Build the Tauri NSIS desktop installer (full pipeline: frontend -> Rust -> NSIS)
build-native:
	$env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
	Set-Location '{{justfile_directory()}}\native'
	npx @tauri-apps/cli build --bundles nsis


# Bootstrap: install dev deps + pre-commit hook
bootstrap:
	uv sync --group dev
	uv run pre-commit install
	Write-Host "Pre-commit hooks installed." -ForegroundColor Green
