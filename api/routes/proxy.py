from fastapi import APIRouter, HTTPException

from opencode_cli_mcp.client import OpencodeClient
from opencode_cli_mcp.job_store import get_job, list_jobs

router = APIRouter(tags=["proxy"])


@router.get("/opencode/status")
async def proxy_status():
    client = OpencodeClient()
    try:
        status = await client.get_server_status()
        return {"success": True, "data": status}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"opencode server unreachable: {e}")
    finally:
        await client.close()


@router.get("/opencode/sessions")
async def proxy_sessions():
    client = OpencodeClient()
    try:
        sessions = await client.list_sessions()
        return {"success": True, "data": {"sessions": sessions}}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        await client.close()


@router.get("/opencode/sessions/{session_id}")
async def proxy_session(session_id: str):
    client = OpencodeClient()
    try:
        session = await client.get_session(session_id)
        return {"success": True, "data": {"session": session}}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        await client.close()


@router.get("/opencode/sessions/{session_id}/diff")
async def proxy_session_diff(session_id: str):
    client = OpencodeClient()
    try:
        diff = await client.get_session_diff(session_id)
        return {"success": True, "data": {"diff": diff}}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        await client.close()


@router.get("/opencode/sessions/{session_id}/files")
async def proxy_session_files(session_id: str):
    client = OpencodeClient()
    try:
        files = await client.get_session_files(session_id)
        return {"success": True, "data": {"files": files}}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    finally:
        await client.close()


@router.get("/runs")
async def proxy_runs():
    jobs = await list_jobs(limit=50)
    return {"success": True, "data": {"runs": jobs}}


@router.get("/runs/{job_id}")
async def proxy_run(job_id: str):
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    return {"success": True, "data": {"run": job}}
