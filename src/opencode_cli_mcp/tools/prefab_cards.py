"""Prefab UI cards (SOTA_REQUIREMENTS SS2.2 - mandatory for list/status tools).

Follows the fleet reference implementation (multi-backup-mcp
src/multi_backup_mcp/tools/prefab_cards.py): @app.tool(app=True) returning
ToolResult with a PrefabApp as structured_content and a plain-text summary
as content for hosts that do not render Apps.

Registration is guarded in server.py: import errors (prefab-ui not yet
synced) or OPENCODE_CLI_MCP_PREFAB_APPS=0 skip these tools without
affecting the rest of the server.
"""

from fastmcp.server.server import ToolResult  # type: ignore[reportPrivateImportUsage]
from prefab_ui import PrefabApp
from prefab_ui.components import Badge, Heading, P, Row

from opencode_cli_mcp.client import get_client
from opencode_cli_mcp.job_store import list_jobs
from opencode_cli_mcp.probe import PROBE_STATE

_STATUS_VARIANT = {
    "completed": "success",
    "running": "info",
    "queued": "info",
    "failed": "error",
    "cancelled": "warning",
}


async def show_runs_app(limit: int = 10) -> ToolResult:
    """Show recent agent runs as a rich Prefab card.

    Lists recent opencode agent runs with status badges. Use the plain
    opencode_runs(action="list") tool when you need raw data instead.

    ## Return Format
    ToolResult with PrefabApp card and plain-text fallback.
    """
    jobs = await list_jobs(limit=limit)

    with PrefabApp(title="OpenCode Agent Runs") as app:
        Heading(f"Agent Runs ({len(jobs)})")
        if jobs:
            for j in jobs:
                Row(label=j["prompt"][:60], value=j["status"])  # type: ignore[reportCallIssue]
                Badge(j["status"], variant=_STATUS_VARIANT.get(j["status"], "info"))
        else:
            P("No agent runs yet.")

    summary = "; ".join(f"{j['job_id']}={j['status']}" for j in jobs) if jobs else "No agent runs yet"
    return ToolResult(content=summary, structured_content=app)


async def show_status_app() -> ToolResult:
    """Show opencode server status as a rich Prefab card.

    Displays opencode serve reachability, startup probe result, and job
    counts. Use opencode_system(action="status") for raw data instead.

    ## Return Format
    ToolResult with PrefabApp card and plain-text fallback.
    """
    client = get_client()
    reachable = await client._ping()
    jobs = await list_jobs(limit=100)
    by_status: dict[str, int] = {}
    for j in jobs:
        by_status[j["status"]] = by_status.get(j["status"], 0) + 1

    with PrefabApp(title="opencode-cli-mcp Status") as app:
        Heading("Server Status")
        Row(label="opencode serve", value=client.base_url)  # type: ignore[reportCallIssue]
        Badge("reachable" if reachable else "unreachable", variant="success" if reachable else "error")
        Row(label="Startup probe", value=str(PROBE_STATE.get("detail")))  # type: ignore[reportCallIssue]
        Heading("Jobs")
        if by_status:
            for status, count in sorted(by_status.items()):
                Row(label=status, value=str(count))  # type: ignore[reportCallIssue]
        else:
            P("No jobs recorded.")

    summary = (
        f"opencode serve {'reachable' if reachable else 'UNREACHABLE'} at {client.base_url}; "
        f"jobs: {by_status or 'none'}"
    )
    return ToolResult(content=summary, structured_content=app)


async def show_sessions_app(limit: int = 10) -> ToolResult:
    """Show opencode sessions as a rich Prefab card.

    Lists recent opencode sessions. Use opencode_sessions(action="list")
    for raw data instead.

    ## Return Format
    ToolResult with PrefabApp card and plain-text fallback.
    """
    client = get_client()
    ok = await client.ensure_server()
    sessions = (await client.list_sessions())[:limit] if ok else []

    with PrefabApp(title="OpenCode Sessions") as app:
        Heading(f"Sessions ({len(sessions)})")
        if not ok:
            Badge("opencode serve unreachable", variant="error")
        elif sessions:
            for s in sessions:
                Row(label=s.get("id", "?"), value=s.get("title", ""))  # type: ignore[reportCallIssue]
        else:
            P("No sessions found.")

    summary = f"{len(sessions)} session(s)" if ok else "opencode serve unreachable"
    return ToolResult(content=summary, structured_content=app)


def register_prefab_tools(app) -> None:
    """Register Prefab card tools on the given FastMCP app."""
    app.tool(app=True)(show_runs_app)
    app.tool(app=True)(show_status_app)
    app.tool(app=True)(show_sessions_app)
