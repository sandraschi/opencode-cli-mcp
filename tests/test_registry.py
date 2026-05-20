from opencode_cli_mcp import registry

REQUIRED_TOOLS = [
    "opencode_run_agent",
    "opencode_get_run_status",
    "opencode_list_runs",
    "opencode_cancel_run",
    "opencode_list_sessions",
    "opencode_get_session",
    "opencode_export_session",
    "opencode_send_message",
    "opencode_get_messages",
    "opencode_session_diff",
    "opencode_session_files",
    "opencode_server_status",
    "opencode_list_providers",
    "opencode_get_project",
]


def test_tool_count():
    assert len(registry.TOOL_DEFINITIONS) == 14


def test_tool_names_match_required():
    names = [t["name"] for t in registry.TOOL_DEFINITIONS]
    assert names == REQUIRED_TOOLS


def test_tool_names_alias():
    assert registry.TOOL_NAMES == [t["name"] for t in registry.TOOL_DEFINITIONS]


def test_all_tools_have_description():
    for t in registry.TOOL_DEFINITIONS:
        assert isinstance(t["description"], str)
        assert len(t["description"]) > 5


def test_all_tools_have_name():
    for t in registry.TOOL_DEFINITIONS:
        assert "name" in t
        assert isinstance(t["name"], str)
        assert len(t["name"]) > 0


def test_tools_importable():
    from opencode_cli_mcp.tools import __all__ as tool_exports

    registered = set(registry.TOOL_NAMES)
    exported = set(tool_exports)
    assert registered == exported


def test_server_uses_registry():
    import inspect

    from opencode_cli_mcp import server

    src = inspect.getsource(server)
    for name in registry.TOOL_NAMES:
        assert name in src, f"Tool {name} not registered in server.py"
