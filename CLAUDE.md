# opencode-cli-mcp

MCP server that wraps opencode's `opencode serve` HTTP API into MCP tools, with a SOTA fleet webapp dashboard.

## Build & Test

- Install: `uv sync`
- Run MCP server: `uv run -m opencode_cli_mcp.server`
- Run webapp backend: `uv run -m api.main`
- Run webapp frontend: `cd web_sota && npm run dev`
- Start all: `.\start.ps1`
- Lint: `uv run ruff check .`
- Type check: `uv run pyright`

## Architecture

- MCP server talks to `opencode serve` HTTP API (default http://127.0.0.1:4096)
- Webapp backend (FastAPI, port 10951) bridges MCP tools to REST
- Webapp frontend (Vite, port 10950) proxies /api to backend
- Ports: 10950 frontend / 10951 backend
