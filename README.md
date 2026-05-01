# opencode-cli-mcp

MCP server that wraps [opencode](https://opencode.ai) CLI's HTTP API (`opencode serve`) into MCP tools, plus a SOTA fleet webapp dashboard.

## Architecture

```
Clients (MCP hosts)  →  opencode-cli-mcp (FastMCP 3.2)
                             ↕ HTTP
                         opencode serve (port 4096)
```

- **MCP Server** (stdio): Exposes 9 tools for agent run, session management, and server status
- **FastAPI Bridge** (port 10951): REST API for the webapp + capability introspection
- **Vite Webapp** (port 10950): SOTA fleet-standard dashboard

## Prerequisites

- [opencode](https://opencode.ai/install) — `npm i -g opencode-ai`
- Python 3.12+ with `uv`
- Node.js 18+ with npm

## Quick Start

```powershell
.\start.ps1
```

This starts opencode serve, the API backend, and the webapp frontend.

Or run individually:

```powershell
uv run -m opencode_cli_mcp.server    # MCP server (stdio)
uv run -m api.main                   # API backend (port 10951)
cd web_sota && npm run dev           # Frontend (port 10950)
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `opencode_run_agent` | Run an agent non-interactively with a prompt |
| `opencode_list_sessions` | List all active/recent sessions |
| `opencode_get_session` | Get detailed session info |
| `opencode_export_session` | Export session as JSON |
| `opencode_send_message` | Send message to a running session |
| `opencode_get_messages` | Retrieve session transcript |
| `opencode_server_status` | Check server health and status |
| `opencode_list_providers` | List configured LLM providers |
| `opencode_get_project` | Get current project context |

## Ports

| Port | Service |
|------|---------|
| 10950 | Frontend (Vite) |
| 10951 | Backend (FastAPI) |
| 4096  | opencode serve |

## License

MIT
