NAME := "opencode-cli-mcp"
DESC := "MCP server wrapping opencode CLI"
VER := "0.1.0"

# Open the interactive recipe dashboard in the browser
default:
    @pwsh.exe -NoProfile -ExecutionPolicy Bypass -File ../mcp-central-docs/scripts/just-dashboard.ps1 -Path .

# ── Development ─────────────────────────────────────────
# Install dependencies
install:
    uv sync
    cd web_sota && npm install

# Run the MCP server (stdio)
serve:
    uv run -m opencode_cli_mcp.server

# Run the API backend
api:
    uv run -m api.main

# Run the webapp frontend
web:
    cd web_sota && npm run dev

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

# Run type checker
type-check:
    uv run pyright

# ── Build ───────────────────────────────────────────────
# Build webapp
build-web:
    cd web_sota && npm run build

# Package MCPB bundle
mcpb-pack:
    mcpb pack . dist/opencode-cli-mcp-v{{VER}}.mcpb
