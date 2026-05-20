TOOL_DEFINITIONS = [
    {"name": "opencode_run_agent", "description": "Run an opencode agent with a prompt. Returns job_id for polling."},
    {"name": "opencode_get_run_status", "description": "Background agent run. Returns output, status, exit code."},
    {"name": "opencode_list_runs", "description": "List all recent agent runs with status and exit codes."},
    {"name": "opencode_cancel_run", "description": "Cancel a running or queued agent run."},
    {"name": "opencode_list_sessions", "description": "List all active and recent opencode sessions."},
    {"name": "opencode_get_session", "description": "Get detailed info about a session including metadata and state."},
    {"name": "opencode_export_session", "description": "Export a session as JSON for archiving or analysis."},
    {"name": "opencode_send_message", "description": "Send a message to an existing session to continue a conversation."},  # noqa: E501
    {"name": "opencode_get_messages", "description": "Retrieve message history/transcript from a session."},
    {"name": "opencode_session_diff", "description": "Show files created, modified, and deleted in a session."},
    {"name": "opencode_session_files", "description": "List all files touched (read, created, modified) in a session."},
    {"name": "opencode_server_status", "description": "Check server health, session count, and config summary."},
    {"name": "opencode_list_providers", "description": "List configured LLM providers in opencode."},
    {"name": "opencode_get_project", "description": "Get the current project context from opencode."},
]

TOOL_NAMES = [t["name"] for t in TOOL_DEFINITIONS]
