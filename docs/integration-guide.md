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

Add in Cursor settings → MCP Servers:

```json
{
  "opencode-cli-mcp": {
    "command": "uv",
    "args": ["run", "-m", "opencode_cli_mcp.server"]
  }
}
```

### Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "opencode-cli-mcp": {
    "command": "uv",
    "args": ["run", "-m", "opencode_cli_mcp.server"]
  }
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENCODE_SERVE_URL` | `http://127.0.0.1:4096` | opencode serve HTTP API base URL |
| `OPENCODE_BINARY` | `opencode` | Path to opencode binary |
| `BACKEND_PORT` | `10951` | FastAPI backend port |

## Workflow Examples

### Run an agent and check results

1. `opencode_server_status` — verify server is running
2. `opencode_run_agent(prompt="Add error handling to src/main.py")` — delegate task
3. `opencode_list_sessions` — find the session ID
4. `opencode_get_session(session_id="...")` — inspect results

### Continue an existing session

1. `opencode_list_sessions` — find session
2. `opencode_send_message(session_id="...", message="Now add tests")` — continue
3. `opencode_get_messages(session_id="...")` — read response

## Webapp

The webapp dashboard is available at `http://localhost:10950` when started via `start.ps1` or `cd web_sota && npm run dev`.
