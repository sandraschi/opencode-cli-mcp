# opencode-cli-mcp

<p align="center">
  <a href="https://github.com/casey/just"><img src="https://img.shields.io/badge/just-ready_to_go-7c5cfc?style=flat-square&logo=just&logoColor=white" alt="Just"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.13+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/PrefectHQ/fastmcp"><img src="https://img.shields.io/badge/FastMCP-3.2-7c5cfc?style=flat-square" alt="FastMCP"></a>
</p>


> 📖 **[Installation Guide](INSTALL.md)** — quick start, manual setup, and troubleshooting

MCP server wrapping [opencode](https://opencode.ai) CLI's HTTP API (`opencode serve`) into 14 FastMCP tools. Also includes a FastAPI REST bridge, a Vite/React fleet-standard dashboard, and [OpenCode custom tools](.opencode/tools/) that extend opencode itself.

**Pattern: Plan with Claude, implement with opencode.** Claude (expensive, high-judgment) orchestrates and supervises; opencode handles implementation grunt work on cheaper models (DeepSeek V4 Flash/Pro).

## Quick Start

```powershell
git clone https://github.com/sandraschi/opencode-cli-mcp
cd opencode-cli-mcp
just
```

This opens an interactive dashboard showing all available commands. Run `just bootstrap` to install dependencies, then `just serve` or `just dev` to start.

### Manual Setup

If you don't have `just` installed:
### Prerequisites
- `opencode` CLI: `npm i -g opencode-ai`
- Python 3.12+
- Node.js 18+
### Run Everything
.\start.ps1
Starts: opencode serve (`:4096`) + FastAPI backend (`:10951`) + Vite frontend (`:10950`).
### MCP Server Only
uv run -m opencode_cli_mcp.server
Configure in Claude Desktop / Cursor / Windsurf (see [Integration Guide](docs/integration-guide.md)).

## 14 MCP Tools

| Tool | Purpose |
|------|---------|
| `opencode_run_agent` | Launch agent (background or blocking) |
| `opencode_get_run_status` | Poll running agent |
| `opencode_list_runs` | List all agent runs |
| `opencode_cancel_run` | Cancel a stuck run |
| `opencode_list_sessions` | List opencode sessions |
| `opencode_get_session` | Session details |
| `opencode_session_diff` | Files changed in a session |
| `opencode_session_files` | Files touched in a session |
| `opencode_export_session` | Export session as JSON |
| `opencode_send_message` | Continue a session |
| `opencode_get_messages` | Session transcript |
| `opencode_server_status` | Server health + config |
| `opencode_list_providers` | Configured LLM providers |
| `opencode_get_project` | Active project context |

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
| [Usage Guide](docs/USAGE.md) | All tools, workflows, async patterns, webapp pages |
| [Integration Guide](docs/integration-guide.md) | MCP client config (Claude Desktop, Cursor, Windsurf) |
| [Advanced Usage](docs/advanced-usage.md) | Async patterns, session management, cross-project, custom tools |
| [Improvement Plan](docs/IMPROVEMENTS_2026-05-02.md) | Known issues and roadmap |
| [Assessment](docs/ASSESSMENT.md) | Architecture review and bug audit |
| [Changelog](CHANGELOG.md) | Version history |

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
