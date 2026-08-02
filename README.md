# opencode-cli-mcp

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.4-7c5cfc?style=flat-square" alt="FastMCP"></a>
</p>


> 📖 **[Installation Guide](INSTALL.md)** - quick start, manual setup, and troubleshooting
> 📖 **[Onboarding](docs/ONBOARDING.md)** - 5-minute first-run guide
> 📖 **[Full reference](llms-full.txt)** - tools, endpoints, env vars, architecture

MCP server wrapping [opencode](https://opencode.ai) CLI's HTTP API (`opencode serve`) into 22 FastMCP tools (7 primary portmanteaus + 15 legacy aliases). Also includes a FastAPI REST bridge (unified with the MCP endpoint on one port), a Vite/React fleet-standard dashboard, and [OpenCode custom tools](.opencode/tools/) that extend opencode itself.

**Pattern: Plan with Claude, implement with opencode.** Claude (expensive, high-judgment) orchestrates and supervises; opencode handles implementation grunt work on cheaper models (DeepSeek V4 Flash/Pro).

> 🧠 **[Eternal Session Memory](docs/ETERNAL_MEMORY.md)** — opencode stores every session since install in one searchable SQLite database. Ask it *"what were we discussing last December about X?"* — no other agentic IDE can do that. opencode-cli-mcp makes that memory searchable, exportable, editable, and backed up.

## What can you do?

| Capability | How |
|-----------|-----|
| **Wayback session find** | `opencode_depot(action="search", query="...")` — full-text (FTS5) across **every** session transcript and title, ever. "What were we working on in December?" |
| **Semantic recall (RAG)** | `opencode_depot(action="rag", query="...")` — embeddings-based similarity over indexed transcripts; find it when you don't remember the words. `rag_index` builds the index, `rag_status` shows state |
| **Read the past** | `opencode_sessions(action="messages"\|"diff"\|"export", session_id=...)` — full transcript, file changes, or a clean markdown/html document |
| **Edit the past** | rename / archive / unarchive / delete sessions (live API or offline depot) |
| **Never lose it** | `opencode_backups(action="create"\|"restore", ...)` — db + config snapshots, rotation, disk guard, autobackup every 24h |
| **Run agents** | `opencode_runs(action="start"\|"status"\|"list"\|"cancel", ...)` — launch, supervise, review |
| **Manage opencode** | `opencode_system(...)` — status, providers, project, MCP pulse, config drift |

## Quick Start

```powershell
git clone https://github.com/sandraschi/opencode-cli-mcp
cd opencode-cli-mcp
just
```

This opens an interactive dashboard showing all available commands. Run `just bootstrap` to install dependencies, then `just serve` to start.

### Manual Setup

If you don't have `just` installed:
### Prerequisites
- `opencode` CLI: `npm i -g opencode-ai`
- Python 3.12+
- Node.js 18+
### Run Everything
.\start.ps1
Starts: opencode serve (`:4096`) + unified backend (`:10951`, REST `/api/*` + MCP `/mcp` on one port) + Vite frontend (`:10950`).
### MCP Server Only
uv run -m opencode_cli_mcp.server
Configure in Claude Desktop / Cursor / Windsurf (see [Integration Guide](docs/integration-guide.md)).

## MCP Tools

Primary surface - seven portmanteaus (operation discriminator):

| Tool | Purpose |
|------|---------|
| `opencode_runs(action=...)` | start / status / list / cancel agent runs |
| `opencode_sessions(action=...)` | list / get / messages / send / diff / grep / export / **rename / delete** sessions (live `opencode serve` API - the opencode UI picks the changes up immediately) |
| `opencode_depot(action=...)` | **eternal memory** - list/archive/unarchive/rename/delete/**search**/stats over the opencode SQLite DB. Full-text search across EVERY session since install, works offline (no `opencode serve` needed). |
| `opencode_backups(action=...)` | **protect the memory** - db + config snapshots (consistent online backup API), rotation, disk-space guard, guarded restore (refuses while serve runs unless force=True) |
| `opencode_system(action=...)` | status / providers / project / launch_ui / mcp_pulse / config_drift |
| `opencode_mcpb_install(...)` | install `.mcpb` bundles into opencode config |
| `opencode_shutdown(confirm=...)` | graceful self-termination |

15 legacy atomic tools remain mounted as aliases through 0.2.x (`opencode_run_agent`, `opencode_get_run_status`, `opencode_list_runs`, `opencode_cancel_run`, `opencode_list_sessions`, `opencode_get_session`, `opencode_send_message`, `opencode_get_messages`, `opencode_session_diff`, `opencode_server_status`, `opencode_list_providers`, `opencode_get_project`, `opencode_get_config`, `opencode_get_health`, `opencode_launch_ui`, plus `opencode_session_grep` / `opencode_export_session` / `opencode_config_drift` / `opencode_mcp_pulse`).

Prefab in-chat cards: `show_runs_app`, `show_sessions_app`, `show_status_app`.

## Eternal Session Memory

opencode records **every conversation and agent run since install** into one
searchable SQLite database (`~/.local/share/opencode/opencode.db`). No other
agentic IDE has this — you cannot ask Claude or Cursor "what were we discussing
last December about santiclaus-mcp?", but you can ask opencode:

```
opencode_depot(action="search", query="santiclaus")          # wayback find - full-text across ALL transcripts
opencode_depot(action="rag", query="santiclaus")             # semantic recall - embeddings over indexed transcripts
opencode_depot(action="rag_index")                           # build the RAG index (once)
opencode_sessions(action="get", session_id="ses_...")        # metadata
opencode_sessions(action="messages", session_id="ses_...")   # the transcript
opencode_sessions(action="export", session_id="ses_...")     # markdown/html document
opencode_backups(action="create", kind="all")                # protect it (autobackup 24h)
```

Full walkthrough: **[docs/ETERNAL_MEMORY.md](docs/ETERNAL_MEMORY.md)** (also on
the webapp **Help** page and Depot page).

## Key Workflows

See [Usage Guide](docs/USAGE.md) for full details.

### Basic: Launch -> Poll -> Review

```
opencode_run_agent(prompt="refactor main.py", wait=false)
    -> { job_id: "abc" }
opencode_get_run_status("abc")     -> poll until completed
opencode_session_diff("session-xyz") -> review changes
```

### Multi-Agent Sweep

Launch N agents across N repos in parallel, poll all, review diffs. Designed for fleet-wide operations.

### Interactive Supervision

Start an agent, read its messages mid-task, send corrections, review final diff.

## OpenCode Custom Tools

Copy `.opencode/tools/*.ts` into your opencode project to give opencode's LLM direct access to MCP fleet management, session inspection, and system diagnostics. 6 tools covering fleet, sessions, runs, system, providers, and tool discovery. See the [OC Tools page](http://localhost:10950/oc-tools) in the webapp for full documentation and source.

## Documentation

| Doc | Description |
|-----|-------------|
| [Onboarding](docs/ONBOARDING.md) | 5-minute first-run guide |
| [Usage Guide](docs/USAGE.md) | All tools, workflows, async patterns, webapp pages |
| [Integration Guide](docs/integration-guide.md) | MCP client config (Claude Desktop, Cursor, Windsurf) |
| [Advanced Usage](docs/advanced-usage.md) | Async patterns, session management, cross-project, custom tools |
| [Improvement Plan](docs/IMPROVEMENTS.md) | Known issues and roadmap |
| [Changelog](CHANGELOG.md) | Version history |

## Stack

- **Backend**: Python 3.12+, FastMCP 3.4.4, FastAPI, uvicorn, httpx, pydantic v2, prefab-ui, psutil, SQLite (job store)
- **Frontend**: React 18, Vite 5, TypeScript, TailwindCSS 3.4, Zustand, Framer Motion, Lucide, React Router, @tauri-apps/api
- **Native**: Tauri 2 (NSIS installer, embedded PyInstaller backend)
- **Quality**: ruff, biome, pytest (+coverage), Playwright e2e, pre-commit, just

## Ports

| Port | Service |
|------|---------|
| 10950 | Frontend (Vite) |
| 10951 | Backend (FastAPI) |
| 4096 | opencode serve |

## Security

This MCP server runs arbitrary shell commands (`opencode run`) from LLM prompts. Only install in environments where you trust your MCP client (Claude Desktop, Cursor) and the models it uses.

## Fleet

- Registered in `mcp-central-docs`: ports 10950/10951
- `fleet-registry.json` and `glama.json` in repo root
- Webapp dashboard: `http://localhost:10950` (run `.\start.ps1`)
