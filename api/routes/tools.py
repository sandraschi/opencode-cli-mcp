from fastapi import APIRouter

router = APIRouter(tags=["tools"])

HARDCODED_TOOLS = [
    {
        "name": "opencode_run_agent",
        "description": "Run an opencode agent non-interactively with a prompt. Delegates coding tasks to the opencode agent.",  # noqa: E501
    },
    {
        "name": "opencode_list_sessions",
        "description": "List all active and recent opencode sessions.",
    },
    {
        "name": "opencode_get_session",
        "description": "Get detailed information about a specific opencode session, including its metadata and state.",  # noqa: E501
    },
    {
        "name": "opencode_export_session",
        "description": "Export an opencode session as JSON. Useful for saving session transcripts.",
    },
    {
        "name": "opencode_send_message",
        "description": "Send a message to an existing opencode session to continue a conversation.",
    },
    {
        "name": "opencode_get_messages",
        "description": "Retrieve message history from an opencode session.",
    },
    {
        "name": "opencode_server_status",
        "description": "Check the status and health of the opencode server.",
    },
    {
        "name": "opencode_list_providers",
        "description": "List configured LLM providers in opencode.",
    },
    {
        "name": "opencode_get_project",
        "description": "Get the current project context from opencode.",
    },
]


@router.get("/tools")
async def list_tools():
    return {"success": True, "data": {"tools": HARDCODED_TOOLS}}
