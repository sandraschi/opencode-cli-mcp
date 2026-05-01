from fastmcp import FastMCP

from opencode_cli_mcp.tools import (
    opencode_export_session,
    opencode_get_messages,
    opencode_get_project,
    opencode_get_session,
    opencode_list_providers,
    opencode_list_sessions,
    opencode_run_agent,
    opencode_send_message,
    opencode_server_status,
)

app = FastMCP("opencode-cli-mcp")

app.tool()(opencode_run_agent)
app.tool()(opencode_list_sessions)
app.tool()(opencode_get_session)
app.tool()(opencode_export_session)
app.tool()(opencode_send_message)
app.tool()(opencode_get_messages)
app.tool()(opencode_server_status)
app.tool()(opencode_list_providers)
app.tool()(opencode_get_project)


@app.prompt()
def agent_instructions():
    """Instructions for using opencode-cli-mcp tools effectively."""
    return """You have access to opencode-cli-mcp tools which wrap opencode's agent capabilities.

**When to use opencode_run_agent:**
- For complex multi-file coding tasks that require a specialized coding agent
- When you need to delegate implementation work to a dedicated agent
- The agent runs as a subprocess with 300s timeout

**When to use session tools:**
- To inspect ongoing or past opencode sessions
- To continue a conversation with a running agent via `opencode_send_message`

**Workflow pattern:**
1. Check server status first with `opencode_server_status`
2. Run agents with `opencode_run_agent`
3. Monitor progress with `opencode_list_sessions` and `opencode_get_session`
4. Export completed sessions with `opencode_export_session`
"""


def main():
    app.run()


if __name__ == "__main__":
    main()
