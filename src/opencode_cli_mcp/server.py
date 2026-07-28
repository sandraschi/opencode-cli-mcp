import os
import sys
from contextlib import asynccontextmanager

from fastmcp import FastMCP

from opencode_cli_mcp.probe import run_startup_probe
from opencode_cli_mcp.tools import TOOL_REGISTRY


@asynccontextmanager
async def _lifespan(server):
    """Startup probe (fastmcp 3.2 fleet standard): shallow, non-fatal
    connectivity check of opencode serve, surfaced via
    opencode_system(action="status")."""
    await run_startup_probe()
    yield {}


app = FastMCP("opencode-cli-mcp", lifespan=_lifespan)

# Single-source registration: every tool (4 primary + 13 legacy
# aliases) comes from TOOL_REGISTRY. registry.py and /api/tools derive
# from the same list, so counts can no longer drift.
for entry in TOOL_REGISTRY:
    app.tool(annotations=entry.annotations or None)(entry.fn)

# Prefab UI cards (SOTA SS2.2). Guarded: prefab-ui not yet synced or
# OPENCODE_CLI_MCP_PREFAB_APPS=0 skips registration without breaking
# the rest of the server.
if os.environ.get("OPENCODE_CLI_MCP_PREFAB_APPS", "1").lower() not in ("0", "false", "no"):
    try:
        from opencode_cli_mcp.tools.prefab_cards import register_prefab_tools

        register_prefab_tools(app)
    except Exception as e:  # pragma: no cover - depends on env
        print(f"[opencode-cli-mcp] Prefab cards not registered: {e}", file=sys.stderr)


@app.prompt()
def agent_instructions():
    """Instructions for using opencode-cli-mcp tools effectively."""
    return """You have access to opencode-cli-mcp tools which wrap opencode's agent capabilities.

**Primary tools (portmanteaus):**
- `opencode_runs(action=...)` — start / status / list / cancel agent runs
- `opencode_sessions(action=...)` — list / get / messages / send / diff sessions
- `opencode_system(action=...)` — status / providers / project / launch_ui / mcp_pulse / config_drift
- `opencode_sessions(action=...)` — list / get / messages / send / diff / grep / export

The granular `opencode_*` tools (run_agent, get_run_status, list_sessions, ...)
are legacy aliases for the same operations and will be removed in 0.3.0.

**Running agents:**
- `opencode_runs(action="start", prompt="...", wait=false)` for long tasks — returns job_id immediately
- `wait=true` for short tasks — blocks until done
- Poll with `opencode_runs(action="status", job_id=...)` for incremental output
- Cancel with `opencode_runs(action="cancel", job_id=...)` if stuck

**Rich views (Prefab, when available):**
- `show_runs_app` / `show_sessions_app` / `show_status_app` render in-chat cards

**Workflow pattern:**
1. `opencode_system(action="status")` — verify opencode serve is reachable
2. `opencode_runs(action="start", prompt="...")` — launch agent, get job_id
3. `opencode_runs(action="status", job_id=...)` — poll until status=completed
4. `opencode_sessions(action="list")` — find the resulting session
5. `opencode_sessions(action="diff", session_id=...)` — review what changed
"""


def main():
    app.run()


if __name__ == "__main__":
    main()
