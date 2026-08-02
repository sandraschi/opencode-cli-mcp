# Changelog

## 0.2.3 - 2026-08-01 (session depot + unified backend)

### Added
- `opencode_depot` portmanteau (6th primary tool): list/get/archive/unarchive/rename/delete/search/stats directly over the opencode SQLite depot (`~/.local/share/opencode/opencode.db`). Works without `opencode serve`; adds unarchive (missing in opencode UI), permanent delete (FK cascade), global transcript search, depot stats. `OPENCODE_DB_PATH` env override for tests/alt installs.
- Experimental light-mode toggle (CSS invert hack, topbar Sun/Moon, persisted `ocmcp-light-mode`). Marked EXPERIMENTAL + reversible per `chat_skills_prefab_standard.md` §7.1.
- CI: `pyright` step (blocking, `src/` + `api/`) - five-gate standard.
- `tests/test_depot.py` (23 tests: filters, pagination, archive round-trip, delete cascade, search, stats, tool surface).
- `GET /api/v1/diagnostics` - CUA smoke-test Phase 7 contract (backend, system, tools, cua_status, errors) with real psutil stats and tool count.
- `just certify` - chains ruff + pytest + pyright + tsc + biome, abort on first failure.

### Fixed
- **Package never installed** (root cause): `pyproject.toml` had no `[build-system]` table, so `uv run python -m api.main` failed with `ModuleNotFoundError` and local dev was broken (only pytest's conftest and the PyInstaller spec worked around it). Added hatchling build config - `uv sync` now installs `opencode-cli-mcp==0.2.3`.
- **Unified backend**: `api.main:app` now serves BOTH REST (`/api/*`) and the FastMCP Streamable HTTP endpoint (`/mcp`, with its lifespan wired) on one port. `fleet-start.config.ps1` points at `api.main:app` - fixes the `/api/v1/health` 404 and the missing MCP mount on the PyInstaller path.
- **opencode serve autostart**: `OPENCODE_BINARY` now resolved via `shutil.which()` - npm-installed `opencode.CMD` shims were never found by `Popen` (CreateProcess only appends `.exe`), so autostart silently failed and the dashboard showed offline.
- Settings page SOTA rewrite: detection-driven provider select (Ollama/LM Studio/vLLM), localStorage persistence (`llm_provider`/`llm_model`), per-provider model lists, vLLM probe, DeepSeek cloud option. Light-mode toggle removed from Settings (it lives in the topbar now).
- pyright: 0 errors across `src/` + `api/` (incl. pre-existing prefab `Div()` runtime bug, `_job` helper typing, cua-smoke `cfg()` typing).
- Version alignment across pyproject.toml, glama.json, capabilities.py `SELF_VERSION`, `api/main.py` FastAPI app version, justfile `VER`, web_sota/package.json, native/tauri.conf.json, native/Cargo.toml - all were still on 0.2.1 or older after the depot release landed.
- `data-testid` sweep: all 15 webapp pages now carry testids (Sessions, StatusAudit, ToolsHub completed; KPIs use fleet `kpi-*` naming).
- Chat page reads the shared Zustand `llmProvider`/`llmModel` (Settings stays owner of detection) - header badge shows `Provider · Model` live.
- justfile `e2e` recipe used `&&` (invalid in the pinned PowerShell 5.1 shell) - now `;`.

## 0.2.2 - 2026-08-01 (assfix)

### Added
- `opencode_shutdown` MCP tool (confirm-guarded self-termination) + `POST /api/shutdown`.
- `GET /api/logs`, `GET /api/logs/export`, `DELETE /api/logs` - ring-buffer request log backing the Logs page (was a dead UI calling a nonexistent endpoint).
- Frontend: `useZoom()` Ctrl+Scroll zoom (Tauri, persisted to `tauri-zoom`), backend status dot with exponential-backoff health poll + Tauri `backend-status` listener + Restart Backend button, dashboard hero with onboarding CTAs.
- Session context injection: `.claude-plugin/`, `hooks/hooks.json`, `.opencode/skills/session-context/`, `.github/copilot-instructions.md`, `## Session Context` in `.cursorrules` + `.windsurfrules`.
- MCPB 3-4-100 prompts: `assets/prompts/system.md`, `user.md`, `examples.json` (103 entries).
- CI: `.github/workflows/ci.yml` (ruff, pytest with coverage, biome, tsc, build on windows-latest).
- Playwright e2e suite (4 tests) + `just e2e`; coverage threshold (`--cov-fail-under=30`, current 49%).
- Biome adoption: `biome.json`, `biome:ci` script, `.pre-commit-config.yaml` + `scripts/pre-commit-biome.ps1`, `.gitattributes` (LF).
- `docs/ONBOARDING.md`.

### Fixed
- CORS: `allow_origin_regex` in `api/main.py` now unconditional fleet regex (Tailscale + LAN), matching the `http_app` middleware on the MCP surface.
- Stale test assertions (tool count 17 → derived from registry; 91 tests green).
- tsc errors (unused `setSort`; `setZoom` moved to `getCurrentWebview`).
- 36 Biome lint violations (button types, label/control pairs, exhaustive deps, index keys, explicit any).
- `just bootstrap` recipe (tab indent, `pre-commit` added to dev deps).
- Version alignment: pyproject/glama/tauri/SELF_VERSION/webapp → 0.2.1.

## 0.2.1 - 2026-07-13

### Added
- `opencode_mcpb_install` tool: install an `.mcpb` bundle into `~/.config/opencode/opencode.json` (unpack manifest, merge server config, write). Supports dry-run, name override, file or directory source.

## 0.2.0 - 2026-07-09

### Added

- **Portmanteau tools** (fleet TOOL_DESIGN_STANDARDS): `opencode_runs` (start/status/list/cancel), `opencode_sessions` (list/get/messages/send/diff), `opencode_system` (status/providers/project/launch_ui). The 13 atomic tools remain mounted as legacy aliases through 0.2.x; removal planned for 0.3.0.
- **SQLite job store** at `%LOCALAPPDATA%\opencode-cli-mcp\jobs.db` (WAL) - shared between the MCP stdio server and the FastAPI backend; the webapp Runs page now shows MCP-launched runs; jobs survive restarts. Cross-process cancel via persisted child PID.
- **Startup probe** (fastmcp 3.2 fleet standard): lifespan pings opencode serve at start; result surfaced via `opencode_system(action="status")`.
- **Prefab UI cards** (SOTA §2.2): `show_runs_app`, `show_status_app`, `show_sessions_app` (`@tool(app=True)`, `ToolResult` + `PrefabApp`, plain-text fallback). `prefab-ui>=0.14.0` is now a core dependency; skip registration with `OPENCODE_CLI_MCP_PREFAB_APPS=0`.
- **Pagination** (limit/offset) on portmanteau list actions; `ToolAnnotations` (readOnly/destructive/idempotent hints) on every tool.
- `Require-Command` naked-PC preflight in `start.ps1` (uv, bun, opencode).

### Fixed

- **start.ps1 was dead on arrival** - `Resolve-FleetPortConflict` was called before `FleetStartMode.ps1` was dot-sourced.
- **Port schism**: Tauri/PyInstaller path used 10700 (virtualization-mcp's registered port). Now 10951 everywhere (run_server.py, backend.rs, Tauri CSP, NSIS config, cua-smoke). run_server.py now reads `OPENCODE_CLI_MCP_PORT`, the env var backend.rs actually sets.
- **Credential-leak trap**: `cloud_key` was persisted into git-visible `api/settings.json`. Settings now live in `%LOCALAPPDATA%\opencode-cli-mcp\settings.json`; `GET /api/settings` redacts the key.
- **Client lifecycle**: tools no longer cold-start and then kill `opencode serve` per call - shared `get_client()` singleton; autostart port derived from `OPENCODE_SERVE_URL`.
- **Job store races**: cancelled jobs no longer flip to "failed"; jobs cancelled while queued never spawn; the stuck-job reaper is lock-safe, respects per-job timeouts, and marks instead of deleting; fire-and-forget tasks hold strong references.
- LM Studio detection parses the endpoint port instead of a `"1234"` substring match.
- `registry.py` is now derived from the single-source `TOOL_REGISTRY` (the hand-maintained copy had drifted - 0.1.0's changelog claimed 14 tools; there were 13).
- `fleet.py` port list derived from the labels dict (probing had missed labeled ports 10769/10808).
- glama.json homepage corrected to `sandraschi`; `uv run python -m …` command form everywhere.

### Changed

- Frontend tooling: npm → **bun** in `start.ps1` (BUN_STANDARDS).
- Version identity: backend/Tauri port is **10951**; requires PyInstaller backend + Tauri rebuild.

## 0.1.0 - 2026-05-05

### Added

- 14 FastMCP tools wrapping opencode serve HTTP API
- FastAPI REST bridge backend (port 10951) with CORS for localhost:10950
- Vite/React/Tailwind webapp dashboard (port 10950) with 11 pages
- Shared tool registry (`registry.py`) as single source of truth for tool definitions
- `ensure_server()` auto-start and health check wired into all session/status tools
- OpenCode custom tools (`.opencode/tools/`) - 6 TypeScript definitions extending opencode with fleet, sessions, runs, system, providers, and tool discovery
- Backend endpoint `GET /api/opencode-tools` serving tool metadata and source
- Backend endpoint `GET /api/docs` and `GET /api/docs/{id}` for documentation serving
- Webapp pages: Dashboard, Sessions, Projects, Tools Hub, OC Tools, Apps Hub, Chat, Help, Settings, Status Audit, API Docs
- Docs endpoint serving markdown from filesystem with auto-discovery
- In-app Help page with document browsing, search, and rendered markdown
- Settings page with theme toggle (applied to document root), opencode URL config, local LLM detection, cloud provider config
- Fleet labels synced from `WEBAPP_PORTS.md` - all 90+ fleet ports now labeled
- `asyncio_mode = "auto"` in pytest config

### Fixed

- `ensure_server()` was dead code - now returns clean error if opencode serve is down
- `/api/tools` was hardcoded - now auto-derived from `registry.py`
- `fleet.py` had 20+ missing labels - all canonical entries from WEBAPP_PORTS.md now included
- GPU detection used deprecated `wmic` - replaced with `Get-CimInstance`
- `opencode_run_agent` blocked event loop with `subprocess.run` - rewritten to `asyncio.create_subprocess_exec`
- 24+ ruff lint errors fixed (imports, bare except, line length, unused variables, multiple statements on one line)
- Help page only showed 3 hardcoded docs as raw `<pre>` - now auto-discovers all docs and renders formatted markdown
- Settings page had mock labels ("Glom On") - replaced with proper labels and real theme application

### Changed

- Line length raised from 100 to 120 for Pillow drawing calls in icon generator
- Theme toggle in Settings applies `dark` class to `document.documentElement`
- Tool descriptions shortened to fit within line-length rules
- API service expanded with typed interfaces for docs, opencode tools
