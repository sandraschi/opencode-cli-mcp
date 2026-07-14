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
    opencode_get_messages,
    opencode_get_session,
    opencode_list_sessions,
    opencode_send_message,
    opencode_session_diff,
)
from opencode_cli_mcp.tools.status import (
    opencode_get_config,
    opencode_get_health,
    opencode_get_project,
    opencode_list_providers,
    opencode_server_status,
)

_READ_ONLY = {"readOnlyHint": True, "idempotentHint": True}
_MUTATING = {"readOnlyHint": False}
_DESTRUCTIVE = {"readOnlyHint": False, "destructiveHint": True}


@dataclass(frozen=True)
class ToolEntry:
    fn: Callable
    annotations: dict[str, Any] = field(default_factory=dict)
    legacy: bool = False

    @property
    def name(self) -> str:
        return self.fn.__name__

    @property
    def description(self) -> str:
        doc = (self.fn.__doc__ or "").strip()
        return doc.splitlines()[0] if doc else ""


TOOL_REGISTRY: list[ToolEntry] = [
    # --- install ---
    ToolEntry(opencode_mcpb_install, _MUTATING),
    # --- portmanteaus (primary surface, TOOL_DESIGN_STANDARDS SS2) ---
    ToolEntry(opencode_runs, {"title": "OpenCode Runs", **_DESTRUCTIVE}),
    ToolEntry(opencode_sessions, {"title": "OpenCode Sessions", **_MUTATING}),
    ToolEntry(opencode_system, {"title": "OpenCode System", **_MUTATING}),
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
    "opencode_runs",
    "opencode_sessions",
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
]
