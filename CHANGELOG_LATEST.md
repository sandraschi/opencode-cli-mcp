# opencode-cli-mcp 0.2.0 — 2026-07-09

Full sprint release: 3 criticals, 5 highs, and the fleet-standards gap closed in one pass.

## Highlights

- **Portmanteau surface**: `opencode_runs` / `opencode_sessions` / `opencode_system` consolidate all 13 atomic tools (which stay mounted as legacy aliases through 0.2.x, removal in 0.3.0). Pagination on list actions, `ToolAnnotations` on everything.
- **SQLite job store** (`%LOCALAPPDATA%\opencode-cli-mcp\jobs.db`, WAL): MCP server and FastAPI backend finally share one store — the webapp Runs page shows real MCP-launched runs, jobs survive restarts, cancel works cross-process.
- **Startup probe** (fastmcp 3.2): opencode serve connectivity checked at server start, surfaced in `opencode_system(action="status")`.
- **Prefab UI cards**: `show_runs_app`, `show_status_app`, `show_sessions_app` (`prefab-ui` now a core dependency; `OPENCODE_CLI_MCP_PREFAB_APPS=0` to skip).

## Critical fixes

- `start.ps1` could never run (function called before its definition was dot-sourced).
- Tauri/PyInstaller backend squatted on **10700 = virtualization-mcp**; one port identity (10951) everywhere now. Requires PyInstaller + Tauri rebuild.
- Settings page persisted `cloud_key` into a git-visible file; settings relocated to LOCALAPPDATA with API-side key redaction. **If a key was ever saved, rotate it.**

## Reliability

- Shared opencode client (no more spawn-then-kill serve churn per tool call).
- Job store: cancel can't be overwritten to "failed", queued-cancel race closed, lock-safe reaper that respects per-job timeouts, strong task references.
- LM Studio detection parses the port (was a `"1234"` substring match).
- Tool registry, capabilities endpoint, and fleet port list all derived from single sources — the 13-vs-14 drift class is dead.

## Tooling

- npm → bun in `start.ps1`; `Require-Command` naked-PC preflight (uv, bun, opencode).
