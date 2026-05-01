from opencode_cli_mcp.client import OpencodeClient


async def opencode_server_status() -> dict:
    """Check the status and health of the opencode server. Returns health info, active session count, and config summary."""  # noqa: E501

    client = OpencodeClient()
    try:
        status = await client.get_server_status()
        return {
            "success": True,
            "message": "Server status retrieved",
            "data": status,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Could not reach opencode server: {e}",
            "data": {},
        }
    finally:
        await client.close()


async def opencode_list_providers() -> dict:
    """List configured LLM providers in opencode."""  # noqa: E501

    client = OpencodeClient()
    try:
        providers = await client.list_providers()
        return {
            "success": True,
            "message": f"Found {len(providers)} providers",
            "data": {"providers": providers},
        }
    finally:
        await client.close()


async def opencode_get_project() -> dict:
    """Get the current project context from opencode. Returns the active project path and metadata."""  # noqa: E501

    client = OpencodeClient()
    try:
        project = await client.get_project()
        return {
            "success": True,
            "message": "Current project retrieved",
            "data": {"project": project},
        }
    finally:
        await client.close()
