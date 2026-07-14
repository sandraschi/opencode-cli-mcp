from opencode_cli_mcp.client import OpencodeClient, get_client


async def _ensure(client: OpencodeClient) -> dict | None:
    if not await client.ensure_server():
        return {"success": False, "message": "opencode serve is not running - start it first", "data": {}}
    return None


async def opencode_server_status() -> dict:
    """Check the status and health of the opencode server. Returns health info, active session count, and config summary."""  # noqa: E501

    client = get_client()
    try:
        err = await _ensure(client)
        if err:
            return err
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


async def opencode_list_providers() -> dict:
    """List configured LLM providers in opencode."""  # noqa: E501

    client = get_client()
    err = await _ensure(client)
    if err:
        return err
    providers = await client.list_providers()
    return {
        "success": True,
        "message": f"Found {len(providers)} providers",
        "data": {"providers": providers},
    }


async def opencode_get_project() -> dict:
    """Get the current project context from opencode. Returns the active project path and metadata."""  # noqa: E501

    client = get_client()
    err = await _ensure(client)
    if err:
        return err
    project = await client.get_project()
    return {
        "success": True,
        "message": "Current project retrieved",
        "data": {"project": project},
    }


async def opencode_get_config() -> dict:
    """Read the full opencode configuration. Returns model, provider, MCP server settings, and instructions."""  # noqa: E501

    client = get_client()
    err = await _ensure(client)
    if err:
        return err
    config = await client.get_config()
    return {
        "success": True,
        "message": "Configuration retrieved",
        "data": {"config": config},
    }


async def opencode_get_health() -> dict:
    """Health check for the opencode server. Returns basic connectivity status and uptime."""  # noqa: E501

    client = get_client()
    try:
        health = await client.get_health()
        return {
            "success": True,
            "message": "Server is healthy",
            "data": health,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Health check failed: {e}",
            "data": {},
        }
