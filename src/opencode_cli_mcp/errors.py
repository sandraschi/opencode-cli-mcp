"""Shared error helpers (TOOL_DESIGN_STANDARDS SS7.1 Pattern 3).

Single place for the fleet dialogic failure shape
``{"success": False, "message": str, "data": dict}`` with automatic
traceback capture: pass the caught exception as ``exc=`` and it is logged
via ``logger.exception`` (never silently swallowed).
"""

import logging

logger = logging.getLogger(__name__)


def error_response(message: str, data: dict | None = None, *, exc: BaseException | None = None) -> dict:
    """Build a dialogic failure return, logging the traceback when given.

    ## Return Format
    {"success": False, "message": str, "data": dict}

    ## Examples
    error_response("Depot error: disk full", {"action": "list"}, exc=e)
    error_response("action 'start' requires 'prompt'")
    """
    if exc is not None:
        logger.exception("[opencode-cli-mcp] %s", message)
    else:
        logger.warning("[opencode-cli-mcp] %s", message)
    return {"success": False, "message": message, "data": data or {}}
