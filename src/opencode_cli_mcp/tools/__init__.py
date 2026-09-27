"""Tool package + single-source registry.

TOOL_REGISTRY is the ONE place tools are enumerated. server.py registers
from it; registry.py (consumed by the REST /api/tools route and
capabilities) derives its definitions from it. This kills the drift that
previously existed between server registrations, registry.py, and the
CHANGELOG (13 vs 14 tools).
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from opencode_cli_mcp.tools.agent import opencode_launch_ui, opencode_run_agent
from opencode_cli_mcp.tools.backups import opencode_backups
from opencode_cli_mcp.tools.depot import opencode_depot
from opencode_cli_mcp.tools.mcpb_install import opencode_mcpb_install
from opencode_cli_mcp.tools.portmanteau import (
    opencode_runs,
    opencode_sessions,
    opencode_system,
)
from opencode_cli_mcp.tools.runs import (
    opencode_cancel_run,
    opencode_get_run_status,
    opencode_list_runs,
)
from opencode_cli_mcp.tools.sessions import (
    opencode_export_session,
    opencode_get_messages,
    opencode_get_session,
    opencode_list_sessions,
    opencode_send_message,
    opencode_session_diff,
    opencode_session_grep,
)
from opencode_cli_mcp.tools.shutdown import opencode_shutdown
from opencode_cli_mcp.tools.status import (
    opencode_config_drift,
    opencode_get_config,
    opencode_get_health,
    opencode_get_project,
    opencode_list_providers,
    opencode_mcp_pulse,
    opencode_server_status,
)

_READ_ONLY = {"readOnlyHint": True, "idempotentHint": True}
_MUTATING = {"readOnlyHint": False}
_DESTRUCTIVE = {"readOnlyHint": False, "destructiveHint": True}

# Fleet dialogic return shape (TOOL_DESIGN_STANDARDS SS4.2/SS8): every
# primary tool returns {"success", "message", "data"}. Declared as the
# structured output schema so MCP clients can validate responses.
_DIALOGIC_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "success": {"type": "boolean"},
        "message": {"type": "string"},
        "data": {"type": "object"},
    },
    "required": ["success", "message", "data"],
}


@dataclass(frozen=True)
class ToolEntry:
    fn: Callable
    annotations: dict[str, Any] = field(default_factory=dict)
    legacy: bool = False
    output_schema: dict[str, Any] | None = None

    @property
    def name(self) -> str:
        return self.fn.__name__

    @property
    def description(self) -> str:
        doc = (self.fn.__doc__ or "").strip()
        return doc.splitlines()[0] if doc else ""


TOOL_REGISTRY: list[ToolEntry] = [
    # --- install ---
    ToolEntry(opencode_mcpb_install, _MUTATING, output_schema=_DIALOGIC_SCHEMA),
    # --- lifecycle ---
    ToolEntry(opencode_shutdown, _DESTRUCTIVE, output_schema=_DIALOGIC_SCHEMA),
    # --- portmanteaus (primary surface, TOOL_DESIGN_STANDARDS SS2) ---
    ToolEntry(opencode_runs, {"title": "OpenCode Runs", **_DESTRUCTIVE}, output_schema=_DIALOGIC_SCHEMA),
    ToolEntry(opencode_sessions, {"title": "OpenCode Sessions", **_MUTATING}, output_schema=_DIALOGIC_SCHEMA),
    ToolEntry(opencode_depot, {"title": "OpenCode Session Depot", **_DESTRUCTIVE}, output_schema=_DIALOGIC_SCHEMA),
    ToolEntry(opencode_backups, {"title": "OpenCode Backups", **_DESTRUCTIVE}, output_schema=_DIALOGIC_SCHEMA),
    ToolEntry(opencode_system, {"title": "OpenCode System", **_MUTATING}, output_schema=_DIALOGIC_SCHEMA),
    # --- legacy atomic tools (aliases through 0.2.x, removal in 0.3.0) ---
    ToolEntry(opencode_run_agent, _MUTATING, legacy=True),
    ToolEntry(opencode_launch_ui, _MUTATING, legacy=True),
    ToolEntry(opencode_list_sessions, _READ_ONLY, legacy=True),
    ToolEntry(opencode_get_session, _READ_ONLY, legacy=True),
    ToolEntry(opencode_send_message, _MUTATING, legacy=True),
    ToolEntry(opencode_get_messages, _READ_ONLY, legacy=True),
    ToolEntry(opencode_session_diff, _READ_ONLY, legacy=True),
    ToolEntry(opencode_server_status, _READ_ONLY, legacy=True),
    ToolEntry(opencode_list_providers, _READ_ONLY, legacy=True),
    ToolEntry(opencode_get_project, _READ_ONLY, legacy=True),
    ToolEntry(opencode_get_config, _READ_ONLY, legacy=True),
    ToolEntry(opencode_get_health, _READ_ONLY, legacy=True),
    ToolEntry(opencode_get_run_status, _READ_ONLY, legacy=True),
    ToolEntry(opencode_list_runs, _READ_ONLY, legacy=True),
    ToolEntry(opencode_cancel_run, _DESTRUCTIVE, legacy=True),
]

__all__ = [
    "TOOL_REGISTRY",
    "ToolEntry",
    "opencode_mcpb_install",
    "opencode_shutdown",
    "opencode_runs",
    "opencode_sessions",
    "opencode_depot",
    "opencode_backups",
    "opencode_system",
    "opencode_launch_ui",
    "opencode_run_agent",
    "opencode_list_sessions",
    "opencode_get_session",
    "opencode_send_message",
    "opencode_get_messages",
    "opencode_session_diff",
    "opencode_server_status",
    "opencode_list_providers",
    "opencode_get_project",
    "opencode_get_run_status",
    "opencode_list_runs",
    "opencode_cancel_run",
    "opencode_mcp_pulse",
    "opencode_session_grep",
    "opencode_export_session",
    "opencode_config_drift",
]
