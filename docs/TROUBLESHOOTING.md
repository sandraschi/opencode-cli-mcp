# Troubleshooting — opencode-cli-mcp

## Every request 500s with `TypeError: 'FastMCP' object is not callable`

Uvicorn is pointed at the raw FastMCP object (`opencode_cli_mcp.server:app`).
The only valid target is the unified app: `api.main:app`
(`fleet-start.config.ps1` → `UvicornTarget`). Fixed 2026-09-15; the config now
carries a comment explaining why.

## Dashboard stuck at "Connecting..." / everything Offline

The backend is up but its event loop is blocked or serve never started:

1. `GET /api/v1/health` — instant `ok`? If it hangs, the loop is blocked
   (fixed 2026-10-05: all depot sqlite calls run in worker threads; earlier
   the 2026-09-15 autobackup freeze: 9GB sync copy in-loop).
2. `opencode serve` unreachable with `Sessions ?` — the backend autostarts its
   own serve on :4097, so this means autostart failed or the serve died:
   - no `opencode` CLI on PATH (scoop shims are missing from service shells).
     Fixed 2026-10-05: `fleet-start.config.ps1` pins `OPENCODE_BINARY` to the
     full shim path. `scoop install opencode`, then restart the backend.
   - stale serve squatting :4097 with a rotated password (401s): the desktop
     app rotates `OPENCODE_SERVER_PASSWORD`, and a serve spawned under the old
     password rejects the new backend while blocking a fresh spawn on the
     port. Kill the :4097 holder; the next serve-dependent call respawns it.
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
