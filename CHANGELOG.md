# Changelog

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
