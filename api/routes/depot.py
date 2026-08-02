"""REST surface for the session depot (offline SQLite access to opencode.db).

Wraps the MCP `opencode_depot` portmanteau functions for the webapp Depot
page. Read-only connections everywhere except the explicit mutating
endpoints (archive/unarchive/rename/delete), which require confirmation
flags and write through the depot module's narrow update path.
"""

import asyncio

from fastapi import APIRouter, HTTPException

from opencode_cli_mcp import depot as d
from opencode_cli_mcp import rag

router = APIRouter(prefix="/depot", tags=["depot"])

_index_task: asyncio.Task | None = None


@router.get("/sessions")
async def depot_list(
    status: str = "all",
    project: str | None = None,
    agent: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort: str = "updated",
    timeframe_days: int | None = None,
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
            timeframe_days=timeframe_days,
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


@router.get("/sessions/{session_id}/transcript")
async def depot_transcript(session_id: str, limit: int = 200):
    """Session text parts with roles/timestamps, read offline from opencode.db."""
    try:
        transcript = d.get_session_transcript(session_id, limit=min(max(limit, 1), 1000))
    except d.DepotError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True, "message": f"{len(transcript)} text parts", "data": {"transcript": transcript}}


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


# --- LanceDB RAG (semantic search over session transcripts) ---------------


@router.get("/rag/status")
async def depot_rag_status():
    return {"success": True, "message": "RAG status", "data": rag.rag_status()}


@router.get("/rag/code")
async def depot_rag_code(q: str = "", path: str = "", limit: int = 20):
    """Code-recall search: when an agent touched a file (patch paths + edits).

    ``path`` alone = lexical path recall; ``q`` (+ optional ``path``) =
    vector search over edit bodies restricted to matching paths.
    """
    try:
        hits = rag.code_search(query=q or None, path_filter=path or None, limit=min(max(limit, 1), 50))
    except rag.RAGUnavailableError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "success": True,
        "message": f"{len(hits)} code matches",
        "data": {"results": hits, "query": q, "path": path},
    }


@router.post("/rag/code/index")
async def depot_rag_code_index():
    """Rebuild the code table from all sessions (code-only backfill)."""
    global _index_task
    if _index_task and not _index_task.done():
        return {"success": True, "message": "Indexing already running", "data": rag.rag_status()}
    try:
        _index_task = asyncio.create_task(asyncio.to_thread(rag.reindex_code_all, 100))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start code index: {e}")
    return {"success": True, "message": "Code indexing started", "data": rag.rag_status()}


@router.post("/rag/index")
async def depot_rag_index(limit_sessions: int | None = None, reset: bool = False):
    """Start (or resume) background indexing of depot sessions.

    ``reset=1`` drops the index and re-indexes from scratch (also used when
    the embedding model changes).
    """
    global _index_task
    if reset:
        from opencode_cli_mcp import rag as _rag

        _rag.reset_index()
    if rag.rag_status().get("running") or (_index_task and not _index_task.done()):
        return {"success": True, "message": "Indexing already running", "data": rag.rag_status()}

    async def _run():
        await asyncio.to_thread(rag.index_new_sessions, limit_sessions)

    _index_task = asyncio.create_task(_run())
    return {"success": True, "message": "Indexing started", "data": rag.rag_status()}


@router.get("/rag/search")
async def depot_rag_search(q: str, limit: int = 20):
    try:
        hits = rag.semantic_search(q, limit=min(max(limit, 1), 50))
    except rag.RAGUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"success": True, "message": f"{len(hits)} semantic matches", "data": {"results": hits, "count": len(hits)}}
