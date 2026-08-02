# opencode-cli-mcp 0.2.3 - 2026-08-01 (session depot + unified backend)

## Added

- `opencode_depot` portmanteau (6th primary tool): list/get/archive/unarchive/rename/delete/search/stats directly over the opencode SQLite depot (`~/.local/share/opencode/opencode.db`). Works without `opencode serve`; adds unarchive (missing in opencode UI), permanent delete (FK cascade), global transcript search, depot stats. `OPENCODE_DB_PATH` env override for tests/alt installs.
- Experimental light-mode toggle (CSS invert hack, topbar Sun/Moon, persisted `ocmcp-light-mode`). Marked EXPERIMENTAL + reversible.
- CI: `pyright` step (blocking, `src/` + `api/`) - five-gate standard.
- `tests/test_depot.py` (23 tests: filters, pagination, archive round-trip, delete cascade, search, stats, tool surface).

## Fixed

- **Unified backend**: `api.main:app` now serves BOTH REST (`/api/*`) and the FastMCP Streamable HTTP endpoint (`/mcp`, with its lifespan wired) on one port. `fleet-start.config.ps1` points at `api.main:app` - fixes the `/api/v1/health` 404 and the missing MCP mount on the PyInstaller path.
- **opencode serve autostart**: `OPENCODE_BINARY` now resolved via `shutil.which()` - npm-installed `opencode.CMD` shims were never found by `Popen`, so autostart silently failed and the dashboard showed offline.
- Settings page SOTA rewrite: detection-driven provider select (Ollama/LM Studio/vLLM), localStorage persistence, per-provider model lists, vLLM probe, DeepSeek cloud option.
- pyright: 0 errors across `src/` + `api/`.
- `GET /api/v1/diagnostics` (was referenced by `scripts/cua-smoke.py` Phase 7 but never implemented - added, returns backend/system/tools/cua_status/errors per the smoke test's contract).
- Version alignment across pyproject.toml, glama.json, capabilities.py `SELF_VERSION`, `api/main.py` FastAPI app version, justfile `VER`, web_sota/package.json, native/tauri.conf.json, native/Cargo.toml - all were still on 0.2.1 or older after the depot release landed.

> Full history: see [CHANGELOG.md](CHANGELOG.md).
