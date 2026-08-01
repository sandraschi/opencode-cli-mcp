import datetime

from fastapi import APIRouter

from opencode_cli_mcp.registry import (
    LEGACY_COUNT,
    PORTMANTEAU_COUNT,
    TOOL_DEFINITIONS,
)

router = APIRouter(tags=["capabilities"])

SELF_VERSION = "0.2.1"


@router.get("/capabilities")
async def get_capabilities():
    """Runtime capability introspection endpoint (WEBAPP_STANDARDS.md §1.4).

    Tool surface is derived from the single-source TOOL_REGISTRY - this
    endpoint can no longer drift from what the MCP server actually mounts.
    """
    portmanteau_tools = [t["name"] for t in TOOL_DEFINITIONS if t["portmanteau"]]
    legacy_tools = [t["name"] for t in TOOL_DEFINITIONS if t["legacy"]]
    return {
        "status": "ok",
        "server": {
            "name": "opencode-cli-mcp",
            "version": SELF_VERSION,
            "fastmcp": "3.4",
        },
        "tool_surface": {
            "total": len(TOOL_DEFINITIONS),
            "portmanteau_count": PORTMANTEAU_COUNT,
            "atomic_count": LEGACY_COUNT,
            "portmanteau_tools": portmanteau_tools,
            "atomic_tools": legacy_tools,
            "legacy_note": "atomic tools are aliases through 0.2.x, removal planned for 0.3.0",
        },
        "features": {
            "sampling": False,
            "agentic_workflows": True,
            "prompts": True,
            "resources": False,
            "skills": False,
            "prefab_apps": True,
            "startup_probe": True,
        },
        "inventory": {
            "workflow_tools": ["opencode_runs", "opencode_sessions", "opencode_system"],
            "prefab_tools": ["show_runs_app", "show_status_app", "show_sessions_app"],
            "prompt_names": ["agent_instructions"],
            "resource_uris": [],
            "skill_uris": [],
        },
        "runtime": {
            "transport": "stdio",
            "surface_mode": "portmanteau+legacy",
        },
        "fleet": {
            "frontend_port": 10950,
            "backend_port": 10951,
            "mcp_command": "uv run python -m opencode_cli_mcp.server",
        },
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }


@router.get("/health")
async def health():
    """Fleet-standard health check."""
    return {"status": "ok", "service": "opencode-cli-mcp-api", "version": SELF_VERSION}


@router.get("/v1/health")
async def v1_health():
    """Canonical fleet health endpoint for cross-fleet probing."""
    return {"status": "ok", "service": "opencode-cli-mcp", "version": SELF_VERSION}
