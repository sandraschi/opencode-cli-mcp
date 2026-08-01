"""Graceful self-termination tool (TOOL_DESIGN_STANDARDS SS1B / 1E).

Deliberately simple: confirm-guarded, logs the reason, then exits the
process after a short delay so the JSON-RPC response flushes first.
"""

import os
import sys
import threading
from typing import Annotated

from pydantic import Field


def opencode_shutdown(
    confirm: Annotated[bool, Field(description="Must be True to shut down the server.")] = False,
    reason: Annotated[str | None, Field(description="Optional reason, recorded in stderr before exit.")] = None,
) -> dict:
    """Shut down this MCP server process gracefully.

    ## Return Format
    {"success": bool, "message": str, "data": dict}

    ## Examples
    opencode_shutdown(confirm=True, reason="maintenance window")
    opencode_shutdown(confirm=False)
    """
    if not confirm:
        return {
            "success": False,
            "message": "Aborted: pass confirm=True to shut down the server.",
            "data": {},
        }
    if reason:
        print(f"[opencode-cli-mcp] shutdown requested: {reason}", file=sys.stderr)
    threading.Timer(0.5, lambda: os._exit(0)).start()
    return {"success": True, "message": "Server shutting down...", "data": {"confirm": True}}
