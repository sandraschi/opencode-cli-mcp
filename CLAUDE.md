# opencode-cli-mcp

MCP server that wraps opencode's `opencode serve` HTTP API into MCP tools, with a SOTA fleet webapp dashboard.

## Build & Test

- Install: `uv sync`
- Run MCP server: `uv run -m opencode_cli_mcp.server`
- Run webapp backend: `uv run python -m api.main`
- Run webapp frontend: `cd web_sota && npm run dev`
- Start all: `.\start.ps1`
- Lint: `uv run ruff check .`
- Test: `uv run pytest`
- TypeScript check: `cd web_sota && npx tsc --noEmit`

## Architecture

- MCP server talks to `opencode serve` HTTP API (default http://127.0.0.1:4096)
- Webapp backend (FastAPI, port 10951) bridges MCP tools to REST
- Webapp frontend (Vite, port 10950) proxies /api to backend
- Tools in `src/opencode_cli_mcp/tools/`: sessions, runs, agent, status
- Shared tool registry in `src/opencode_cli_mcp/registry.py`
- `ensure_server()` is wired into all session/status tools
- OpenCode custom tools in `.opencode/tools/` — TS definitions calling backend API
- Docs served via `GET /api/docs`, tool source via `GET /api/opencode-tools`
- Ports: 10950 frontend / 10951 backend / 4096 opencode

## Key Patterns

- `opencode_run_agent(prompt, wait=false)` launches background agent
- `opencode_get_run_status(job_id)` polls for completion
- `opencode_session_diff(session_id)` reviews changes
- `opencode_cancel_run(job_id)` kills stuck agent

## API Routes

| Prefix | Purpose |
|--------|---------|
| `/api/capabilities` | Health + runtime introspection |
| `/api/opencode/*` | Proxy to opencode serve |
| `/api/runs/*` | Agent run tracking |
| `/api/tools` | Tool definitions |
| `/api/fleet` | Fleet app status |
| `/api/system` | OS/GPU/memory info |
| `/api/docs/*` | Documentation serving |
| `/api/opencode-tools/*` | OpenCode custom tool definitions |
| `/api/settings` | App settings CRUD |

## Webapp Pages (11)

Dashboard, Sessions, Projects, Tools Hub, OC Tools, Apps Hub, Chat, Help, Settings, Status Audit, API Docs
