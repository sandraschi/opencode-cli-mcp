from opencode_cli_mcp import registry

PRIMARY_TOOLS = [
    "opencode_mcpb_install",
    "opencode_runs",
    "opencode_sessions",
    "opencode_system",
]

LEGACY_TOOLS = [
    "opencode_run_agent",
    "opencode_launch_ui",
    "opencode_get_run_status",
    "opencode_list_runs",
    "opencode_cancel_run",
    "opencode_list_sessions",
    "opencode_get_session",
    "opencode_send_message",
    "opencode_get_messages",
    "opencode_session_diff",
    "opencode_server_status",
    "opencode_list_providers",
    "opencode_get_project",
]


def test_tool_count():
    assert len(registry.TOOL_DEFINITIONS) == 17
    assert registry.PORTMANTEAU_COUNT == 4
    assert registry.LEGACY_COUNT == 13


def test_tool_names_complete():
    names = set(registry.TOOL_NAMES)
    assert names == set(PRIMARY_TOOLS) | set(LEGACY_TOOLS)


def test_primary_tool_flags():
    for t in registry.TOOL_DEFINITIONS:
        if t["name"] in PRIMARY_TOOLS:
            assert t["portmanteau"] is True and t["legacy"] is False
        else:
            assert t["portmanteau"] is False and t["legacy"] is True


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


def test_registry_matches_tool_registry():
    # registry.py is derived, not hand-maintained: it must mirror TOOL_REGISTRY.
    from opencode_cli_mcp.tools import TOOL_REGISTRY

    assert registry.TOOL_NAMES == [e.name for e in TOOL_REGISTRY]


def test_all_registry_entries_have_annotations():
    from opencode_cli_mcp.tools import TOOL_REGISTRY

    for e in TOOL_REGISTRY:
        assert isinstance(e.annotations, dict) and e.annotations, f"{e.name} missing annotations"
        assert "readOnlyHint" in e.annotations
