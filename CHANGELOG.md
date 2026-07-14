# Changelog

## 0.2.1 — 2026-07-13

### Added
- `opencode_mcpb_install` tool: install an `.mcpb` bundle into `~/.config/opencode/opencode.json` (unpack manifest, merge server config, write). Supports dry-run, name override, file or directory source.

## 0.2.0 — 2026-07-09

### Added

- **Portmanteau tools** (fleet TOOL_DESIGN_STANDARDS): `opencode_runs` (start/status/list/cancel), `opencode_sessions` (list/get/messages/send/diff), `opencode_system` (status/providers/project/launch_ui). The 13 atomic tools remain mounted as legacy aliases through 0.2.x; removal planned for 0.3.0.
- **SQLite job store** at `%LOCALAPPDATA%\opencode-cli-mcp\jobs.db` (WAL) — shared between the MCP stdio server and the FastAPI backend; the webapp Runs page now shows MCP-launched runs; jobs survive restarts. Cross-process cancel via persisted child PID.
- **Startup probe** (fastmcp 3.2 fleet standard): lifespan pings opencode serve at start; result surfaced via `opencode_system(action="status")`.
- **Prefab UI cards** (SOTA §2.2): `show_runs_app`, `show_status_app`, `show_sessions_app` (`@tool(app=True)`, `ToolResult` + `PrefabApp`, plain-text fallback). `prefab-ui>=0.14.0` is now a core dependency; skip registration with `OPENCODE_CLI_MCP_PREFAB_APPS=0`.
- **Pagination** (limit/offset) on portmanteau list actions; `ToolAnnotations` (readOnly/destructive/idempotent hints) on every tool.
- `Require-Command` naked-PC preflight in `start.ps1` (uv, bun, opencode).

### Fixed

- **start.ps1 was dead on arrival** — `Resolve-FleetPortConflict` was called before `FleetStartMode.ps1` was dot-sourced.
- **Port schism**: Tauri/PyInstaller path used 10700 (virtualization-mcp's registered port). Now 10951 everywhere (run_server.py, backend.rs, Tauri CSP, NSIS config, cua-smoke). run_server.py now reads `OPENCODE_CLI_MCP_PORT`, the env var backend.rs actually sets.
- **Credential-leak trap**: `cloud_key` was persisted into git-visible `api/settings.json`. Settings now live in `%LOCALAPPDATA%\opencode-cli-mcp\settings.json`; `GET /api/settings` redacts the key.
- **Client lifecycle**: tools no longer cold-start and then kill `opencode serve` per call — shared `get_client()` singleton; autostart port derived from `OPENCODE_SERVE_URL`.
- **Job store races**: cancelled jobs no longer flip to "failed"; jobs cancelled while queued never spawn; the stuck-job reaper is lock-safe, respects per-job timeouts, and marks instead of deleting; fire-and-forget tasks hold strong references.
- LM Studio detection parses the endpoint port instead of a `"1234"` substring match.
- `registry.py` is now derived from the single-source `TOOL_REGISTRY` (the hand-maintained copy had drifted — 0.1.0's changelog claimed 14 tools; there were 13).
- `fleet.py` port list derived from the labels dict (probing had missed labeled ports 10769/10808).
- glama.json homepage corrected to `sandraschi`; `uv run python -m …` command form everywhere.

### Changed

- Frontend tooling: npm → **bun** in `start.ps1` (BUN_STANDARDS).
- Version identity: backend/Tauri port is **10951**; requires PyInstaller backend + Tauri rebuild.

## 0.1.0 — 2026-05-05

### Added

- 14 FastMCP tools wrapping opencode serve HTTP API
- FastAPI REST bridge backend (port 10951) with CORS for localhost:10950
- Vite/React/Tailwind webapp dashboard (port 10950) with 11 pages
- Shared tool registry (`registry.py`) as single source of truth for tool definitions
- `ensure_server()` auto-start and health check wired into all session/status tools
- OpenCode custom tools (`.opencode/tools/`) — 6 TypeScript definitions extending opencode with fleet, sessions, runs, system, providers, and tool discovery
- Backend endpoint `GET /api/opencode-tools` serving tool metadata and source
- Backend endpoint `GET /api/docs` and `GET /api/docs/{id}` for documentation serving
- Webapp pages: Dashboard, Sessions, Projects, Tools Hub, OC Tools, Apps Hub, Chat, Help, Settings, Status Audit, API Docs
- Docs endpoint serving markdown from filesystem with auto-discovery
- In-app Help page with document browsing, search, and rendered markdown
- Settings page with theme toggle (applied to document root), opencode URL config, local LLM detection, cloud provider config
- Fleet labels synced from `WEBAPP_PORTS.md` — all 90+ fleet ports now labeled
- `asyncio_mode = "auto"` in pytest config

### Fixed

- `ensure_server()` was dead code — now returns clean error if opencode serve is down
- `/api/tools` was hardcoded — now auto-derived from `registry.py`
- `fleet.py` had 20+ missing labels — all canonical entries from WEBAPP_PORTS.md now included
- GPU detection used deprecated `wmic` — replaced with `Get-CimInstance`
- `opencode_run_agent` blocked event loop with `subprocess.run` — rewritten to `asyncio.create_subprocess_exec`
- 24+ ruff lint errors fixed (imports, bare except, line length, unused variables, multiple statements on one line)
- Help page only showed 3 hardcoded docs as raw `<pre>` — now auto-discovers all docs and renders formatted markdown
- Settings page had mock labels ("Glom On") — replaced with proper labels and real theme application

### Changed

- Line length raised from 100 to 120 for Pillow drawing calls in icon generator
- Theme toggle in Settings applies `dark` class to `document.documentElement`
- Tool descriptions shortened to fit within line-length rules
- API service expanded with typed interfaces for docs, opencode tools
