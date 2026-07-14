"""Portmanteau tools (fleet TOOL_DESIGN_STANDARDS SS2).

Three consolidated tools covering the full surface of the 13 legacy atomic
tools, which remain mounted as aliases for one release (0.2.x) and will be
removed in 0.3.0. Portmanteaus add pagination (limit/offset) on list actions.
"""

from typing import Annotated, Literal

from pydantic import Field

from opencode_cli_mcp.job_store import list_jobs
from opencode_cli_mcp.probe import PROBE_STATE
from opencode_cli_mcp.tools.agent import opencode_launch_ui, opencode_run_agent
from opencode_cli_mcp.tools.runs import opencode_cancel_run, opencode_get_run_status
from opencode_cli_mcp.tools.sessions import (
    opencode_get_messages,
    opencode_get_session,
    opencode_list_sessions,
    opencode_send_message,
    opencode_session_diff,
)
from opencode_cli_mcp.tools.status import (
    opencode_get_project,
    opencode_list_providers,
    opencode_server_status,
)


def _missing(action: str, param: str) -> dict:
    return {
        "success": False,
        "message": f"action '{action}' requires '{param}'",
        "data": {},
        "recovery_options": [f"Call again with {param} set."],
    }


async def opencode_runs(
    action: Annotated[
        Literal["start", "status", "list", "cancel"],
        Field(description="start: launch an agent run. status: poll a run. list: recent runs. cancel: stop a run."),
    ],
    prompt: Annotated[str | None, Field(description="Agent prompt (required for start)")] = None,
    job_id: Annotated[str | None, Field(description="Job ID (required for status/cancel)")] = None,
    project: Annotated[str | None, Field(description="Project directory (optional, start)")] = None,
    output_format: Annotated[Literal["text", "json"], Field(description="Output format (start)")] = "text",
    wait: Annotated[bool, Field(description="Block until done (start; default false = fire-and-forget)")] = False,
    timeout: Annotated[int, Field(description="Max seconds for the run (start)", ge=1, le=86400)] = 300,
    limit: Annotated[int, Field(description="Page size (list)", ge=1, le=100)] = 20,
    offset: Annotated[int, Field(description="Page offset (list)", ge=0)] = 0,
) -> dict:
    """Manage opencode agent runs: start, poll status, list recent, or cancel.

    ## Return Format
    {"success": bool, "message": str, "data": dict}
    Fire-and-forget starts return a job_id; poll with action="status".
    """

    if action == "start":
        if not prompt:
            return _missing("start", "prompt")
        return await opencode_run_agent(
            prompt=prompt, project=project, format=output_format, wait=wait, timeout=timeout
        )
    if action == "status":
        if not job_id:
            return _missing("status", "job_id")
        return await opencode_get_run_status(job_id=job_id)
    if action == "cancel":
        if not job_id:
            return _missing("cancel", "job_id")
        return await opencode_cancel_run(job_id=job_id)

    # list (paginated)
    jobs = await list_jobs(limit=limit, offset=offset)
    return {
        "success": True,
        "message": f"Found {len(jobs)} runs (offset {offset})",
        "data": {
            "runs": [
                {
                    "job_id": j["job_id"],
                    "prompt": j["prompt"],
                    "status": j["status"],
                    "exit_code": j["exit_code"],
                    "created_at": j["created_at"],
                    "completed_at": j["completed_at"],
                }
                for j in jobs
            ],
            "limit": limit,
            "offset": offset,
            "next_offset": offset + limit if len(jobs) == limit else None,
        },
    }


async def opencode_sessions(
    action: Annotated[
        Literal["list", "get", "messages", "send", "diff"],
        Field(
            description="list: all sessions. get: one session. messages: transcript. send: message a session. diff: files changed."
        ),
    ],
    session_id: Annotated[str | None, Field(description="Session ID (required for get/messages/send/diff)")] = None,
    message: Annotated[str | None, Field(description="Message text (required for send)")] = None,
    limit: Annotated[int, Field(description="Page size (list/messages)", ge=1, le=200)] = 50,
    offset: Annotated[int, Field(description="Page offset (list)", ge=0)] = 0,
) -> dict:
    """Inspect and interact with opencode sessions: list, get, read transcript, send a message, or diff changed files.

    ## Return Format
    {"success": bool, "message": str, "data": dict}
    """

    if action == "list":
        result = await opencode_list_sessions()
        if not result.get("success"):
            return result
        sessions = result["data"]["sessions"]
        page = sessions[offset : offset + limit]
        return {
            "success": True,
            "message": f"Found {len(page)} of {len(sessions)} sessions (offset {offset})",
            "data": {
                "sessions": page,
                "total": len(sessions),
                "limit": limit,
                "offset": offset,
                "next_offset": offset + limit if offset + limit < len(sessions) else None,
            },
        }
    if not session_id:
        return _missing(action, "session_id")
    if action == "get":
        return await opencode_get_session(session_id=session_id)
    if action == "messages":
        return await opencode_get_messages(session_id=session_id, limit=limit)
    if action == "diff":
        return await opencode_session_diff(session_id=session_id)
    # send
    if not message:
        return _missing("send", "message")
    return await opencode_send_message(session_id=session_id, message=message)


async def opencode_system(
    action: Annotated[
        Literal["status", "providers", "project", "launch_ui"],
        Field(
            description="status: health + startup probe. providers: LLM providers. project: current project. launch_ui: open opencode."
        ),
    ],
    mode: Annotated[Literal["tui", "web", "serve"], Field(description="Launch mode (launch_ui)")] = "tui",
    project: Annotated[str | None, Field(description="Project directory (launch_ui)")] = None,
) -> dict:
    """opencode server and environment: health/status (incl. startup probe), providers, current project, or launch the UI.

    ## Return Format
    {"success": bool, "message": str, "data": dict}
    """

    if action == "providers":
        return await opencode_list_providers()
    if action == "project":
        return await opencode_get_project()
    if action == "launch_ui":
        return await opencode_launch_ui(project=project, mode=mode)

    # status: server status + startup probe result
    result = await opencode_server_status()
    if isinstance(result.get("data"), dict):
        result["data"]["startup_probe"] = dict(PROBE_STATE)
    return result
