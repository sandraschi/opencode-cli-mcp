# opencode-cli-mcp — Agent Guide

## Overview

MCP server wrapping the [opencode](https://opencode.ai) CLI (`opencode serve`) for AI agent
orchestration: launch/poll/review agent runs, session CRUD + diff, offline session depot over
the opencode SQLite DB, `.mcpb` installs, and graceful shutdown. Ships a unified FastAPI backend
(REST `/api/*` + FastMCP `/mcp` on one port) and a Vite/React fleet-standard dashboard.

## Quick-Ref Commands

| Command | What it does |
|---------|--------------|
| `just serve` | Run MCP server (stdio) |
| `just api` | Run unified backend (`api.main`, :10951) |
| `just web` | Run Vite frontend (:10950) |
| `just certify` | All gates: ruff, pytest, pyright, tsc, biome |
| `just test` / `just check` | pytest / ruff check + format |
| `.\start.ps1` | Full stack: opencode serve + backend + frontend |

## Ports

| Port | Service |
|------|---------|
| 10950 | Frontend (Vite) |
| 10951 | Unified backend (REST `/api/*` + MCP `/mcp`) |
| 4096 | opencode serve |

## Standards

- FastMCP 3.2+ portmanteau tool pattern — tools use `operation` enum param; responses are
  structured dicts with `success`, `message`, domain-specific fields.
- 6 primary tools (`opencode_runs`, `opencode_sessions`, `opencode_depot`, `opencode_system`,
  `opencode_mcpb_install`, `opencode_shutdown`) + 15 legacy atomic aliases (0.3.0 removes them).
- Dual transport: stdio (Claude Desktop) + unified HTTP backend (`api.main`).
- See [mcp-central-docs](https://github.com/sandraschi/mcp-central-docs) for fleet-wide standards.

## Key Files

| File | Purpose |
|------|---------|
| `src/opencode_cli_mcp/server.py` | FastMCP app + `http_app` (CORS-wrapped ASGI) |
| `src/opencode_cli_mcp/client.py` | httpx client → opencode serve; `OPENCODE_BINARY` resolution |
| `src/opencode_cli_mcp/depot.py` | Session depot (direct SQLite on opencode.db) |
| `src/opencode_cli_mcp/registry.py` | Shared tool definitions |
| `api/main.py` | Unified ASGI app (REST + MCP `/mcp`) |
| `api/routes/capabilities.py` | `/api/health`, `/api/v1/health`, `/api/v1/diagnostics` |
| `web_sota/src/store.ts` | Zustand store (incl. shared `llmProvider`/`llmModel`) |
| `run_server.py` | PyInstaller entry point (`OPENCODE_CLI_MCP_PORT` → HTTP) |
