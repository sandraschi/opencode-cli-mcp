import pytest

from opencode_cli_mcp.server import app


def test_server_initialization():
    assert app.name == "opencode-cli-mcp"


@pytest.mark.asyncio
async def test_tools_registered():
    tools = await app.list_tools()
    tool_names = {t.name for t in tools}
    assert "opencode_run_agent" in tool_names
    assert "opencode_list_sessions" in tool_names
    assert "opencode_get_session" in tool_names
    assert "opencode_export_session" in tool_names
    assert "opencode_send_message" in tool_names
    assert "opencode_get_messages" in tool_names
    assert "opencode_server_status" in tool_names
    assert "opencode_list_providers" in tool_names
    assert "opencode_get_project" in tool_names
    assert "opencode_get_run_status" in tool_names
    assert "opencode_list_runs" in tool_names
    assert "opencode_cancel_run" in tool_names
    assert "opencode_session_diff" in tool_names
    assert "opencode_session_files" in tool_names
    assert len(tool_names) == 14


@pytest.mark.asyncio
async def test_prompts_registered():
    prompts = await app.list_prompts()
    prompt_names = {p.name for p in prompts}
    assert "agent_instructions" in prompt_names
