import pytest

from opencode_cli_mcp.registry import TOOL_NAMES
from opencode_cli_mcp.server import app


def test_server_initialization():
    assert app.name == "opencode-cli-mcp"


@pytest.mark.asyncio
async def test_all_registry_tools_mounted():
    tools = await app.list_tools()
    tool_names = {t.name for t in tools}
    # Every tool in the single-source registry must actually be mounted.
    missing = set(TOOL_NAMES) - tool_names
    assert not missing, f"Registry tools not mounted: {missing}"


@pytest.mark.asyncio
async def test_portmanteaus_mounted():
    tools = await app.list_tools()
    tool_names = {t.name for t in tools}
    assert {"opencode_runs", "opencode_sessions", "opencode_system"} <= tool_names


@pytest.mark.asyncio
async def test_tool_count_floor():
    tools = await app.list_tools()
    # 3 portmanteaus + 13 legacy aliases; +3 Prefab cards when prefab-ui is
    # installed (registration is guarded, so count may be 16 or 19).
    assert len(tools) >= 16


@pytest.mark.asyncio
async def test_prompts_registered():
    prompts = await app.list_prompts()
    prompt_names = {p.name for p in prompts}
    assert "agent_instructions" in prompt_names
