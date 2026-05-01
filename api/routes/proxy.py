from fastapi import APIRouter, HTTPException

from opencode_cli_mcp.client import OpencodeClient

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
