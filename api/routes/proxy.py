from fastapi import APIRouter, HTTPException

from opencode_cli_mcp.client import OpencodeClient, get_client
from opencode_cli_mcp.job_store import get_job, list_jobs
from opencode_cli_mcp.tools.agent import opencode_run_agent
from opencode_cli_mcp.tools.runs import opencode_cancel_run

router = APIRouter(tags=["proxy"])


async def _get_client() -> OpencodeClient:
    client = get_client()
    await client.ensure_server()
    return client


@router.get("/opencode/status")
async def proxy_status():
    client = await _get_client()
    try:
        status = await client.get_server_status()
        return {"success": True, "data": status}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"opencode server unreachable: {e}")


@router.get("/mcp/status")
async def proxy_mcp_status():
    """Per-server MCP connection status from opencode serve (GET /mcp).

    Powers the webapp MCP Servers page status dots (Cursor-style). Can be
    slow when many configured servers are down - serve probes each one.
    """
    client = await _get_client()
    try:
        status = await client.get_mcp_status()
        return {"success": True, "data": {"servers": status}}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"MCP status unavailable: {e}")


@router.get("/opencode/sessions")
async def proxy_sessions():
    client = await _get_client()
    try:
        sessions = await client.list_sessions()
        return {"success": True, "data": {"sessions": sessions}}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/opencode/sessions/{session_id}")
async def proxy_session(session_id: str):
    client = await _get_client()
    try:
        session = await client.get_session(session_id)
        return {"success": True, "data": {"session": session}}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {e}")


@router.get("/opencode/sessions/{session_id}/diff")
async def proxy_session_diff(session_id: str):
    client = await _get_client()
    try:
        diff = await client.get_session_diff(session_id)
        return {"success": True, "data": {"diff": diff}}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session diff failed: {e}")


@router.get("/opencode/sessions/{session_id}/messages")
async def proxy_session_messages(session_id: str, limit: int = 200):
    """Transcript messages for one session (drives the webapp transcript view)."""
    client = await _get_client()
    try:
        messages = await client.get_messages(session_id, limit=min(max(limit, 1), 500))
        return {"success": True, "data": {"messages": messages}}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session messages failed: {e}")


@router.patch("/opencode/sessions/{session_id}")
async def proxy_session_rename(session_id: str, body: dict):
    """Rename a session via the live opencode serve API (session.update).

    Preferred over the depot route while opencode is running: the server
    updates its in-memory session too, so the opencode UI reflects the new
    title immediately and cannot overwrite it with the stale auto-title.
    """
    title = (body.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="title required")
    client = await _get_client()
    try:
        updated = await client.update_session(session_id, title)
        return {"success": True, "message": f"Renamed '{session_id}'", "data": {"session": updated}}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session rename failed: {e}")


@router.delete("/opencode/sessions/{session_id}")
async def proxy_session_delete(session_id: str, confirm: bool = False):
    """Delete a session via the live opencode serve API (session.delete)."""
    if not confirm:
        raise HTTPException(status_code=422, detail="confirm=true required - deletion is permanent")
    client = await _get_client()
    try:
        result = await client.delete_session(session_id)
        return {"success": True, "message": f"Deleted '{session_id}' permanently", "data": {"result": result}}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session delete failed: {e}")


@router.get("/runs")
async def proxy_runs():
    jobs = await list_jobs(limit=50)
    return {"success": True, "data": {"runs": jobs}}


@router.post("/runs")
async def proxy_start_run(body: dict):
    """Launch an opencode agent run from the webapp (populates the Projects page).

    body: {prompt, project?, format? ("text"|"json"), wait? (bool), timeout?}
    Reuses the MCP tool logic - same job store, same process spawn.
    """
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=422, detail="prompt required")
    if len(prompt) > 8000:
        raise HTTPException(status_code=422, detail="prompt too long (max 8000 chars)")
    try:
        result = await opencode_run_agent(
            prompt=prompt,
            project=(body.get("project") or "").strip() or None,
            format="json" if body.get("format") == "json" else "text",
            wait=bool(body.get("wait", False)),
            timeout=max(1, min(int(body.get("timeout", 300)), 86400)),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start run: {e}")
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("message", "failed to start run"))
    return result


@router.post("/runs/{job_id}/cancel")
async def proxy_cancel_run(job_id: str):
    result = await opencode_cancel_run(job_id=job_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message", "cancel failed"))
    return result


@router.get("/runs/{job_id}")
async def proxy_run(job_id: str):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return {"success": True, "data": {"run": job}}
