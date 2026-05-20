from fastapi import APIRouter

from opencode_cli_mcp.registry import TOOL_DEFINITIONS

router = APIRouter(tags=["tools"])


@router.get("/tools")
async def list_tools():
    return {"success": True, "data": {"tools": TOOL_DEFINITIONS}}
