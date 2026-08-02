"""REST surface for the session depot (offline SQLite access to opencode.db).

Wraps the MCP `opencode_depot` portmanteau functions for the webapp Depot
page. Read-only connections everywhere except the explicit mutating
endpoints (archive/unarchive/rename/delete), which require confirmation
flags and write through the depot module's narrow update path.
"""

from fastapi import APIRouter, HTTPException

from opencode_cli_mcp import depot as d

router = APIRouter(prefix="/depot", tags=["depot"])


@router.get("/sessions")
async def depot_list(
    status: str = "all",
    project: str | None = None,
    agent: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort: str = "updated",
):
    try:
        data = d.list_sessions(
            status=status,
            project=project,
            agent=agent,
            search=search,
            limit=min(max(limit, 1), 200),
            offset=max(offset, 0),
            sort=sort,
        )
    except d.DepotError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True, "message": f"Found {data['total']} sessions", "data": data}


@router.get("/sessions/{session_id}")
async def depot_get(session_id: str):
    try:
        session = d.get_session(session_id)
    except d.DepotError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return {"success": True, "message": "Session found", "data": {"session": session}}


@router.get("/search")
async def depot_search(q: str, limit: int = 20, include_archived: bool = True):
    try:
        data = d.search_transcripts(q, limit=min(max(limit, 1), 100), include_archived=include_archived)
    except d.DepotError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True, "message": f"{data['count']} transcript matches", "data": data}


@router.get("/stats")
async def depot_stats():
    try:
        data = d.depot_stats()
    except d.DepotError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True, "message": "Depot stats", "data": data}


@router.post("/sessions/{session_id}/archive")
async def depot_archive(session_id: str):
    try:
        ok = d.archive_session(session_id)
    except d.DepotError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return {"success": True, "message": f"Archived '{session_id}'"}


@router.post("/sessions/{session_id}/unarchive")
async def depot_unarchive(session_id: str):
    try:
        ok = d.unarchive_session(session_id)
    except d.DepotError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return {"success": True, "message": f"Unarchived '{session_id}'"}


@router.patch("/sessions/{session_id}")
async def depot_rename(session_id: str, body: dict):
    title = (body.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="title required")
    try:
        ok = d.rename_session(session_id, title)
    except d.DepotError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return {"success": True, "message": f"Renamed '{session_id}'"}


@router.delete("/sessions/{session_id}")
async def depot_delete(session_id: str, confirm: bool = False):
    if not confirm:
        raise HTTPException(status_code=422, detail="confirm=true required - deletion is permanent (FK cascade)")
    try:
        ok = d.delete_session(session_id)
    except d.DepotError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if not ok:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return {"success": True, "message": f"Deleted '{session_id}' permanently"}
