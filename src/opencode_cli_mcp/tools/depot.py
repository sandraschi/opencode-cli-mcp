"""opencode_depot portmanteau - direct session-depot CRUD + analytics.

Complements opencode_sessions (live interaction via `opencode serve`):
the depot reads the SQLite DB opencode writes, so it works even when
serve is down, and it covers the operations the serve API lacks:
archive, unarchive, rename, delete, global transcript search, stats.
"""

from typing import Annotated, Literal

from pydantic import Field

from opencode_cli_mcp import depot


def _missing(action: str, param: str) -> dict:
    return {
        "success": False,
        "message": f"action '{action}' requires '{param}'",
        "data": {},
        "recovery_options": [f"Call again with {param} set."],
    }


def _not_found(action: str, session_id: str) -> dict:
    return {
        "success": False,
        "message": f"Session {session_id} not found in depot",
        "data": {},
        "recovery_options": ["List sessions first: opencode_depot(action='list')"],
    }


def _wrap(action: str, ok: bool, message: str, data: dict) -> dict:
    return {"success": ok, "message": message, "data": data}


async def opencode_depot(
    action: Annotated[
        Literal["list", "get", "archive", "unarchive", "rename", "delete", "search", "stats"],
        Field(
            description=(
                "list: sessions with filters. get: one session with counts."
                " archive: hide from active list. unarchive: restore (missing in opencode UI)."
                " rename: set title. delete: permanently remove (cascades messages)."
                " search: full-text across transcripts and titles."
                " stats: aggregate cost/tokens by agent/project."
            )
        ),
    ],
    session_id: Annotated[
        str | None, Field(description="Session ID (required for get/archive/unarchive/rename/delete)")
    ] = None,
    title: Annotated[str | None, Field(description="New title (rename)")] = None,
    query: Annotated[str | None, Field(description="Search text (search)")] = None,
    status: Annotated[
        Literal["all", "active", "archived"],
        Field(description="Status filter (list): all, active, or archived"),
    ] = "all",
    project: Annotated[str | None, Field(description="Project/directory substring filter (list)")] = None,
    agent: Annotated[str | None, Field(description="Agent name filter (list)")] = None,
    search: Annotated[str | None, Field(description="Title substring filter (list)")] = None,
    sort: Annotated[
        Literal["updated", "created", "archived", "cost", "tokens", "title"],
        Field(description="Sort order (list)"),
    ] = "updated",
    limit: Annotated[int, Field(description="Page size (list/search)", ge=1, le=200)] = 50,
    offset: Annotated[int, Field(description="Page offset (list)", ge=0)] = 0,
) -> dict:
    """Session depot: list, inspect, archive/unarchive, rename, delete, search transcripts, or stats.

    Reads opencode's SQLite depot directly - works without `opencode serve`.
    Archive/unarchive/rename are reversible; delete is permanent (FK cascade).

    ## Return Format
    {"success": bool, "message": str, "data": dict}

    ## Examples
    opencode_depot(action="list", status="archived", limit=20)
    opencode_depot(action="unarchive", session_id="sess_01")
    opencode_depot(action="search", query="power limit")
    opencode_depot(action="stats")
    """

    try:
        return await _dispatch(action, session_id, title, query, status, project, agent, search, sort, limit, offset)
    except depot.DepotError as e:
        return _wrap(action, False, str(e), {})
    except Exception as e:  # pragma: no cover - defensive boundary
        return _wrap(action, False, f"Depot error: {e}", {})


async def _dispatch(
    action: str,
    session_id: str | None,
    title: str | None,
    query: str | None,
    status: str,
    project: str | None,
    agent: str | None,
    search: str | None,
    sort: str,
    limit: int,
    offset: int,
) -> dict:
    if action == "list":
        page = depot.list_sessions(
            status=status, project=project, agent=agent, search=search, limit=limit, offset=offset, sort=sort
        )
        return _wrap(
            action,
            True,
            f"Found {page['total']} sessions ({page['offset']}+{len(page['sessions'])})",
            {"filters": {"status": status, "project": project, "agent": agent, "search": search}, **page},
        )

    if action == "search":
        if not query:
            return _missing(action, "query")
        result = depot.search_transcripts(query, limit=limit)
        return _wrap(action, True, f"Found {result['count']} transcript matches for '{query}'", result)

    if action == "stats":
        return _wrap(action, True, "Depot statistics", depot.depot_stats())

    if not session_id:
        return _missing(action, "session_id")

    if action == "get":
        session = depot.get_session(session_id)
        if session is None:
            return _not_found(action, session_id)
        return _wrap(action, True, f"Session {session_id}", {"session": session})

    if action == "archive":
        if depot.archive_session(session_id):
            return _wrap(action, True, f"Archived session {session_id}", {"session_id": session_id, "archived": True})
        return _not_found(action, session_id)

    if action == "unarchive":
        if depot.unarchive_session(session_id):
            return _wrap(
                action, True, f"Restored session {session_id} to active", {"session_id": session_id, "archived": False}
            )
        return _not_found(action, session_id)

    if action == "rename":
        if not title:
            return _missing(action, "title")
        if depot.rename_session(session_id, title):
            return _wrap(action, True, f"Renamed session {session_id}", {"session_id": session_id, "title": title})
        return _not_found(action, session_id)

    # delete
    if depot.delete_session(session_id):
        return _wrap(action, True, f"Deleted session {session_id} (permanent)", {"session_id": session_id})
    return _not_found(action, session_id)
