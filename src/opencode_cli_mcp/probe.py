"""Startup probe (fastmcp 3.2 fleet standard).

Shallow, non-fatal connectivity check of opencode serve at server start.
Result is kept in PROBE_STATE and surfaced via opencode_system(action="status")
and the status Prefab card. Logs to stderr only - stdout belongs to the MCP
stdio protocol and must stay clean.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

PROBE_STATE: dict[str, Any] = {
    "ran": False,
    "opencode_serve": None,
    "url": None,
    "checked_at": None,
    "detail": "startup probe has not run",
}


async def run_startup_probe() -> dict[str, Any]:
    from opencode_cli_mcp.client import get_client

    client = get_client()
    try:
        ok = await client._ping()
    except Exception as e:  # never let the probe kill server startup
        ok = False
        detail = f"probe error: {e}"
    else:
        detail = (
            "opencode serve reachable" if ok else "opencode serve not reachable (will autostart on first tool call)"
        )

    PROBE_STATE.update(
        ran=True,
        opencode_serve=ok,
        url=client.base_url,
        checked_at=time.time(),
        detail=detail,
    )
    logger.warning("[opencode-cli-mcp] startup probe: %s (%s)", detail, client.base_url)
    return dict(PROBE_STATE)
