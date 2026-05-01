from fastapi import APIRouter

router = APIRouter(tags=["capabilities"])


@router.get("/capabilities")
async def get_capabilities():
    """Runtime capability introspection endpoint."""
    return {
        "status": "ok",
        "server": {
            "name": "opencode-cli-mcp",
            "version": "0.1.0",
            "fastmcp": "3.2",
        },
        "tool_surface": {
            "total": 9,
            "portmanteau_count": 0,
            "atomic_count": 9,
            "portmanteau_tools": [],
            "atomic_tools": [
                "opencode_run_agent",
                "opencode_list_sessions",
                "opencode_get_session",
                "opencode_export_session",
                "opencode_send_message",
                "opencode_get_messages",
                "opencode_server_status",
                "opencode_list_providers",
                "opencode_get_project",
            ],
        },
        "features": {
            "sampling": False,
            "agentic_workflows": False,
            "prompts": True,
            "resources": False,
            "skills": False,
        },
        "inventory": {
            "workflow_tools": [],
            "prompt_names": ["agent_instructions"],
            "resource_uris": [],
            "skill_uris": [],
        },
        "runtime": {
            "transport": "stdio",
            "surface_mode": "atomic",
        },
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }


@router.get("/health")
async def health():
    return {"status": "ok", "service": "opencode-cli-mcp-api"}
