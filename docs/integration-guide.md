# opencode-cli-mcp Integration Guide

## MCP Client Configuration

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "opencode-cli-mcp": {
      "command": "uv",
      "args": ["run", "-m", "opencode_cli_mcp.server"],
      "env": {
        "OPENCODE_SERVE_URL": "http://127.0.0.1:4096"
      }
    }
  }
}
```

### Cursor IDE

Cursor settings -> MCP Servers -> Add:

```json
{
  "opencode-cli-mcp": {
    "command": "uv",
    "args": ["run", "-m", "opencode_cli_mcp.server"]
  }
}
```

### Windsurf

```json
// ~/.codeium/windsurf/mcp_config.json
{
  "opencode-cli-mcp": {
    "command": "uv",
    "args": ["run", "-m", "opencode_cli_mcp.server"]
  }
}
```

## Prerequisites

1. **Install opencode CLI:** `npm i -g opencode-ai`
2. **Start opencode serve:** `opencode serve` (or use `start.ps1`)
3. **Verify:** `opencode_server_status` should return health info

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENCODE_SERVE_URL` | `http://127.0.0.1:4096` | opencode serve HTTP API base URL |
| `OPENCODE_BINARY` | `opencode` | Path to opencode binary |
| `BACKEND_PORT` | `10951` | FastAPI backend port (webapp only) |

## Workflow Examples

### Verify Setup

```
opencode_server_status
  -> success, health info, session count
```

### Delegate a Task

```
opencode_run_agent(prompt="Add error handling to src/main.py")
  -> job_id, status=running

opencode_get_run_status(job_id)
  -> poll until status=completed
  -> read stdout/stderr

opencode_session_diff(session_id)
  -> see what files changed
```

### Continue a Session

```
opencode_list_sessions
opencode_send_message(session_id="abc", message="Now add tests")
opencode_get_messages(session_id)
```

### Fleet Sweep

```
opencode_run_agent(prompt="update deps", project="./repo-a", wait=false)
opencode_run_agent(prompt="update deps", project="./repo-b", wait=false)
# poll both...
```

## Webapp Dashboard

Start with `.\start.ps1`, then open `http://localhost:10950`.

Available pages:
- Dashboard: health, stats, system info
- Sessions: browse opencode sessions
- Tools Hub: explore all 14 tools with schemas
- Fleet Apps: discover running fleet services
- Chat: local LLM chat (Ollama)
- Settings: theme, LLM config
- Status Audit: CPU/GPU/memory/logs
- API Docs: Swagger UI + ReDoc

## Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| "opencode serve not running" | Server not started | Run `opencode serve` or `.\start.ps1` |
| Tool returns empty data | Wrong session ID | Use `opencode_list_sessions` to find valid IDs |
| Agent times out | Task too long for default 300s | Set `timeout` parameter higher |
| No providers listed | opencode not configured | Configure providers in opencode first |
