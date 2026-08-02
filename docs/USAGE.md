# opencode-cli-mcp Usage Guide

## Quick Reference

### Primary MCP Tools (6 portmanteaus)

| Tool | Purpose |
|------|---------|
| `opencode_runs(action=...)` | start / status / list / cancel agent runs |
| `opencode_sessions(action=...)` | list / get / messages / send / diff / grep / export sessions |
| `opencode_depot(action=...)` | **session depot** - list/archive/unarchive/rename/delete/search/stats over the opencode SQLite DB (works offline) |
| `opencode_system(action=...)` | status / providers / project / launch_ui / mcp_pulse / config_drift |
| `opencode_mcpb_install(...)` | install `.mcpb` bundles into opencode config |
| `opencode_shutdown(confirm=...)` | graceful self-termination |

15 legacy atomic aliases remain mounted through 0.2.x (`opencode_run_agent`, `opencode_list_sessions`, `opencode_get_session`, `opencode_send_message`, `opencode_get_messages`, `opencode_session_diff`, `opencode_server_status`, `opencode_list_providers`, `opencode_get_project`, `opencode_get_config`, `opencode_get_health`, `opencode_get_run_status`, `opencode_list_runs`, `opencode_cancel_run`, `opencode_launch_ui`, plus `opencode_session_grep` / `opencode_export_session` / `opencode_config_drift` / `opencode_mcp_pulse`).

---

## Workflows

### 1. Launch, Poll, Review (Basic)

```
opencode_run_agent(prompt="refactor main.py", wait=false)
    -> { job_id: "abc123" }

opencode_get_run_status("abc123")
    -> { status: "completed", stdout: "...", exit_code: 0 }

opencode_list_sessions
    -> find the resulting session

opencode_session_diff("session-xyz")
    -> { diff: { created: [...], modified: [...], deleted: [...] } }
```

### 2. Concurrent Multi-Agent Sweep

Launch several agents in parallel, poll all, review results:

```
# Fire off N agents
agent_1 = opencode_run_agent(prompt="lint fix aiwatcher-mcp", project="D:/repos/aiwatcher-mcp", wait=false)
agent_2 = opencode_run_agent(prompt="lint fix arxiv-mcp", project="D:/repos/arxiv-mcp", wait=false)
agent_3 = opencode_run_agent(prompt="lint fix plex-mcp", project="D:/repos/plex-mcp", wait=false)

# Poll until all complete
for each job_id:
    opencode_get_run_status(job_id)

# Review diffs
opencode_session_diff(session_id_from_agent_1)
opencode_session_diff(session_id_from_agent_2)
```

### 3. Interactive Supervision

```
# Start agent on a task
opencode_run_agent(prompt="implement OAuth2 in api/routes/auth.py")

# Check progress
opencode_get_messages(session_id)
  -> reads what the agent is doing

# Intervene mid-task
opencode_send_message(session_id, "Add rate limiting too")

# Review final changes
opencode_session_diff(session_id)
opencode_get_messages(session_id)
```

### 4. Archive and Review

```
# List recent work
opencode_list_runs(limit=10)
  -> all runs, their status, and session references

# Review conversation history
opencode_get_messages("session-xyz")
  -> returns full conversation transcript
```

---

## Async vs Sync

| Mode | Usage | Returns |
|------|-------|---------|
| `wait=false` (default) | Fire-and-forget long tasks | `{ job_id }` immediately |
| `wait=true` | Short tasks, block until done | `{ status, stdout, exit_code }` |

With `wait=false`, use `opencode_get_run_status(job_id)` to poll.

---

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENCODE_SERVE_URL` | `http://127.0.0.1:4096` | opencode HTTP API URL |
| `OPENCODE_BINARY` | `opencode` | Path to opencode CLI |
| `BACKEND_PORT` | `10951` | Webapp backend port |

---

## Architecture

```
Claude Desktop / Cursor / Windsurf
    |
    | stdio (MCP)
    v
opencode-cli-mcp (FastMCP 3.2)
    |
    | httpx
    v
opencode serve (HTTP :4096)
    |
    | subprocess
    v
opencode agent (DeepSeek / configured model)

Web Dashboard (optional): http://localhost:10950
  Frontend (:10950) -> Backend API (:10951) -> opencode serve (:4096)
```

---

## Ports

| Port | Service |
|------|---------|
| 10950 | Frontend (Vite dev server) |
| 10951 | Backend (FastAPI) |
| 4096 | opencode serve |

---

## OpenCode Custom Tools

6 TypeScript tools in `.opencode/tools/` that extend opencode with MCP fleet awareness, session management, and system diagnostics. Each tool calls the FastAPI backend (port 10951).

| Tool File | Tool Names | Category | Purpose |
|-----------|------------|----------|---------|
| `fleet.ts` | `fleet_status`, `fleet_launch` | Fleet | Check fleet server status, launch apps |
| `sessions.ts` | `sessions_list`, `sessions_diff`, `sessions_files` | Sessions | List, diff, inspect opencode sessions |
| `runs.ts` | `runs_list`, `runs_status` | Runs | List and inspect background agent runs |
| `system.ts` | `system` | System | CPU, memory, GPU, platform diagnostics |
| `providers.ts` | `providers` | System | LLM provider list and server health |
| `tools.ts` | `tools` | Meta | List all MCP tools the server exposes |

### Installation

Copy the tool files into your opencode project:

```
cp -r .opencode/tools/* your-project/.opencode/tools/
```

Restart opencode - tools are auto-loaded on start. See the webapp [OC Tools page](http://localhost:10950/oc-tools) for source code and full documentation.

---

## Webapp Pages (11)

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | Health, stats, system info |
| `/sessions` | Sessions | Browse opencode sessions |
| `/projects` | Projects | OpenCode project listing |
| `/tools` | Tools Hub | Explore all 14 MCP tools |
| `/oc-tools` | OC Tools | OpenCode custom tools install + source |
| `/apps` | Fleet Apps | Discover running fleet services |
| `/chat` | Chat | Local LLM chat (Ollama) |
| `/help` | Help | In-app documentation browser |
| `/settings` | Settings | Theme, opencode URL, LLM config |
| `/status` | Status Audit | CPU, GPU, memory, logs |
| `/api-docs` | API Docs | Swagger/ReDoc |
