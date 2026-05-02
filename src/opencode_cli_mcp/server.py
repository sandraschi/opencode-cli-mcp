from fastmcp import FastMCP

from opencode_cli_mcp.tools import (
    opencode_cancel_run,
    opencode_export_session,
    opencode_get_messages,
    opencode_get_project,
    opencode_get_run_status,
    opencode_get_session,
    opencode_list_providers,
    opencode_list_runs,
    opencode_list_sessions,
    opencode_run_agent,
    opencode_send_message,
    opencode_server_status,
    opencode_session_diff,
    opencode_session_files,
)

app = FastMCP("opencode-cli-mcp")

app.tool()(opencode_run_agent)
app.tool()(opencode_list_sessions)
app.tool()(opencode_get_session)
app.tool()(opencode_export_session)
app.tool()(opencode_send_message)
app.tool()(opencode_get_messages)
app.tool()(opencode_session_diff)
app.tool()(opencode_session_files)
app.tool()(opencode_server_status)
app.tool()(opencode_list_providers)
app.tool()(opencode_get_project)
app.tool()(opencode_get_run_status)
app.tool()(opencode_list_runs)
app.tool()(opencode_cancel_run)


@app.prompt()
def agent_instructions():
    """Instructions for using opencode-cli-mcp tools effectively."""
    return """You have access to opencode-cli-mcp tools which wrap opencode's agent capabilities.

**When to use opencode_run_agent:**
- Set `wait=false` (default) for long tasks — returns job_id immediately
- Set `wait=true` for short tasks — blocks until done
- Poll with `opencode_get_run_status(job_id)` for incremental output
- Cancel with `opencode_cancel_run(job_id)` if stuck

**When to use session tools:**
- `opencode_list_sessions` / `opencode_get_session` — inspect opencode sessions
- `opencode_session_diff(session_id)` — see what files changed
- `opencode_session_files(session_id)` — see files touched
- `opencode_export_session(session_id)` — archive a session

**When to use run tools:**
- `opencode_list_runs` — see all agent runs
- `opencode_get_run_status(job_id)` — poll a running agent
- `opencode_cancel_run(job_id)` — cancel a stuck run

**Workflow pattern:**
1. `opencode_server_status` — verify server is running
2. `opencode_run_agent(prompt="...", wait=false)` — launch agent, get job_id
3. `opencode_get_run_status(job_id)` — poll until status=completed
4. `opencode_list_sessions` — find the resulting session
5. `opencode_session_diff(session_id)` — review what changed
"""


def main():
    app.run()


if __name__ == "__main__":
    main()
