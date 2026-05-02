# opencode-cli-mcp

MCP server that wraps [opencode](https://opencode.ai) CLI's HTTP API (`opencode serve`) into MCP tools, plus a SOTA fleet-standard webapp dashboard.

## Quick Start

```powershell
.\start.ps1                  # OpenCode serve + API + frontend
uv run -m opencode_cli_mcp.server    # MCP server only (stdio)
```

Requires: `opencode` CLI (`npm i -g opencode-ai`), Python 3.12+, Node.js 18+.

## MCP Tools (14 atomic)

| Tool | Purpose |
|------|---------|
| `opencode_run_agent` | Launch agent (background or blocking) |
| `opencode_get_run_status` | Poll running agent for progress |
| `opencode_list_runs` | List all agent runs |
| `opencode_cancel_run` | Cancel a stuck run |
| `opencode_list_sessions` | List opencode sessions |
| `opencode_get_session` | Session details |
| `opencode_session_diff` | What files changed in a session |
| `opencode_session_files` | Files touched in a session |
| `opencode_export_session` | Export session as JSON |
| `opencode_send_message` | Continue a running session |
| `opencode_get_messages` | Session transcript |
| `opencode_server_status` | Server health + config |
| `opencode_list_providers` | Configured LLM providers |
| `opencode_get_project` | Active project context |

### Async Workflow (recommended)

```
opencode_run_agent(prompt="refactor main.py", wait=false)
    → { job_id: "abc123" }

opencode_get_run_status("abc123")       # poll until completed
    → { status: "completed", stdout: "...", exit_code: 0 }

opencode_session_diff("session-xyz")     # review changes
    → { diff: { created: [...], modified: [...], deleted: [...] } }
```

## Architecture

```
MCP hosts  →  opencode-cli-mcp (FastMCP 3.2, stdio)
                   ↕ httpx
              opencode serve (HTTP :4096)
```

## Ports

| Port | Service |
|------|---------|
| 10950 | Frontend (Vite) |
| 10951 | Backend (FastAPI) |
| 4096  | opencode serve |

## Security

This MCP server runs arbitrary shell commands (`opencode run`) from LLM prompts.
Only install and use in environments where you trust your MCP client (Claude Desktop,
Cursor, etc.) and the models it uses.

## Fleet

- Registered in `mcp-central-docs`: ports 10950/10951
- Start script: `.\start.ps1` (supports `-Headless`)
- Glama: `glama.json` in repo root
