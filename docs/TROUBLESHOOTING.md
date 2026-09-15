# Troubleshooting — opencode-cli-mcp

## Every request 500s with `TypeError: 'FastMCP' object is not callable`

Uvicorn is pointed at the raw FastMCP object (`opencode_cli_mcp.server:app`).
The only valid target is the unified app: `api.main:app`
(`fleet-start.config.ps1` → `UvicornTarget`). Fixed 2026-09-15; the config now
carries a comment explaining why.

## Dashboard stuck at "Connecting..." / everything Offline

The backend is up but its event loop is blocked or serve never started:

1. `GET /api/v1/health` — instant `ok`? If it hangs, the loop is blocked
   (the 2026-09-15 autobackup freeze: 9GB sync copy in-loop; fixed with grace
   period + worker thread).
2. `opencode serve` Offline with `Sessions ?` — no `opencode` CLI installed
   (the desktop app bundles none). `scoop install opencode`, restart the backend
   so the binary resolves, then any serve-dependent call autostarts :4097.
3. Port squatting — an old backend still holds :10951 (`start.ps1` clears ports;
   otherwise stop the owning PID).

## `EADDRINUSE` on restart

Kill the holder: `Get-NetTCPConnection -LocalPort 10951` → `Stop-Process`.
`start.ps1` does this automatically.

## Serve on :4096 returns 401

That's the desktop app's password-protected serve. The backend uses its own on
:4097 (`OPENCODE_SERVE_URL`). To talk to the desktop's, set
`OPENCODE_SERVER_PASSWORD` (+ optional `OPENCODE_SERVER_USERNAME`).

## RAG endpoints 503 / `RAGUnavailableError`

`fastembed`/`lancedb`/`pyarrow` missing or disabled (`OPENCODE_CLI_MCP_RAG_ENABLED`).
`uv sync --extra rag`. First index downloads the embedding model (slow once).

## Restore refused while serve runs

By design (a live server resurrects rows). Stop serve first or pass force — see
`opencode_backups(action="restore")`.
