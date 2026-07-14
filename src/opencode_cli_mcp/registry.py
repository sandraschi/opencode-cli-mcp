"""Tool definitions derived from the single-source TOOL_REGISTRY.

Previously a hand-maintained duplicate list that had already drifted
(13 entries vs the CHANGELOG's claimed 14). Now generated from
opencode_cli_mcp.tools.TOOL_REGISTRY - names and descriptions come
straight from the registered functions and their docstrings.
"""

from opencode_cli_mcp.tools import TOOL_REGISTRY

TOOL_DEFINITIONS = [
    {
        "name": e.name,
        "description": e.description,
        "portmanteau": not e.legacy,
        "legacy": e.legacy,
    }
    for e in TOOL_REGISTRY
]

TOOL_NAMES = [t["name"] for t in TOOL_DEFINITIONS]
PORTMANTEAU_COUNT = sum(1 for e in TOOL_REGISTRY if not e.legacy)
LEGACY_COUNT = sum(1 for e in TOOL_REGISTRY if e.legacy)
