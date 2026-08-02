import datetime
import shutil

from fastapi import APIRouter

from api import logs as _logs
from opencode_cli_mcp.registry import (
    LEGACY_COUNT,
    PORTMANTEAU_COUNT,
    TOOL_DEFINITIONS,
)

router = APIRouter(tags=["capabilities"])

SELF_VERSION = "0.2.3"


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


@router.get("/v1/diagnostics")
async def v1_diagnostics():
    """CUA-NSIS smoke-test contract (scripts/cua-smoke.py Phase 7).

    system.cpu_percent/memory_percent/disk_percent use psutil when available,
    0.0 otherwise (psutil is an optional dependency, not vendored here to
    keep this route import-cheap on non-Windows dev machines).

    cua_status.window_found is always False: this backend process has no
    window of its own to introspect (that's the Tauri shell's UI, a
    separate process) - the CUA smoke test is expected to fill this in
    from its own pywinauto probe, not trust this endpoint for it.
    """
    try:
        import psutil

        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage("/").percent
    except ImportError:
        cpu_percent = memory_percent = disk_percent = 0.0

    error_entries, error_count = _logs.entries(limit=_logs.MAX_ENTRIES, level="ERROR")

    return {
        "success": True,
        "data": {
            "backend": {"status": "running", "version": SELF_VERSION},
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
            },
            "tools": {"total": len(TOOL_DEFINITIONS)},
            "cua_status": {
                "tesseract_available": shutil.which("tesseract") is not None,
                "window_found": False,
            },
            "errors": {"count": error_count, "recent": [e["detail"] for e in error_entries[:5]]},
        },
    }
