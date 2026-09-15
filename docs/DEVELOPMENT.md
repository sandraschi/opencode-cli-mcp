# Development — opencode-cli-mcp

## Layout

| Path | Purpose |
|------|---------|
| `src/opencode_cli_mcp/` | FastMCP server (`server.py`), depot (`depot.py`), RAG (`rag.py`), backups (`backup.py`), serve client (`client.py`), tools (`tools/`) |
| `api/` | Unified FastAPI backend (`main.py` + `routes/`); mounts the MCP app at `/` |
| `web_sota/` | Vite/React dashboard (npm shop: `npm ci`, `npm run biome:ci`, `npx tsc --noEmit`) |
| `native/` | Tauri shell (NSIS target) |
| `sidebar/` | AHK desktop companion (outside the `.mcpb`; see `docs/SIDEBAR.md`) |
| `mcpb/` | Bundle staging (`pack.ps1` wipes + recopies `src/` before pack) |

## Gates (all must pass)

```powershell
uv run ruff check src api
uv run ruff format src api --check
uv run pyright src api
uv run pytest tests -q          # 158 tests, coverage gate 30%
```

Web: `npm run biome:ci`, `npx tsc --noEmit` in `web_sota/`. Full pass: `just certify`.

## Running

- `just serve` — MCP server (stdio, for Claude Desktop).
- `just api` — unified backend on :10951.
- `just web` — frontend on :10950.
- `.\start.ps1` — full stack (engine or standalone fallback with port clearing,
  `uv sync` guard, and `/api/v1/health` readiness gate).

## Backend debugging

- Health: `GET /api/v1/health`, diagnostics: `GET /api/v1/diagnostics`.
- The backend autostarts its own `opencode serve` on :4097 on first serve-dependent
  call. If status shows Offline, check the `opencode` CLI resolves
  (`shutil.which`) — the desktop app bundles no CLI.
- Autobackup runs deferred (5-min grace) in a worker thread — never inline in the
  event loop (a 9GB synchronous copy once froze all request handling).
- Tests run against `src/` (editable-install guard in CI); if pytest passes but the
  app misbehaves, re-check which `opencode_cli_mcp` gets imported.
