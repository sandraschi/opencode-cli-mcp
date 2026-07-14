from typing import Annotated

from pydantic import Field

from opencode_cli_mcp.client import OpencodeClient, get_client


async def _ensure(client: OpencodeClient) -> dict | None:
    if not await client.ensure_server():
        return {"success": False, "message": "opencode serve is not running - start it first", "data": {}}
    return None


async def opencode_list_sessions() -> dict:
    """List all active and recent opencode sessions."""  # noqa: E501

    client = get_client()
    err = await _ensure(client)
    if err:
        return err
    sessions = await client.list_sessions()
    return {
        "success": True,
        "message": f"Found {len(sessions)} sessions",
        "data": {"sessions": sessions},
    }


async def opencode_get_session(
    session_id: Annotated[str, Field(description="Session ID to retrieve")],
) -> dict:
    """Get detailed information about a specific opencode session, including its metadata and state."""  # noqa: E501

    client = get_client()
    err = await _ensure(client)
    if err:
        return err
    session = await client.get_session(session_id)
    return {
        "success": True,
        "message": f"Retrieved session {session_id}",
        "data": {"session": session},
    }


async def opencode_send_message(
    session_id: Annotated[str, Field(description="Session ID to send message to")],
    message: Annotated[str, Field(description="Message text to send to the agent")],
) -> dict:
    """Send a message to an existing opencode session. Use this to continue a conversation with a running agent."""  # noqa: E501

    client = get_client()
    err = await _ensure(client)
    if err:
        return err
    result = await client.send_message(session_id, message)
    return {
        "success": True,
        "message": "Message sent to session",
        "data": {"result": result},
    }


async def opencode_session_diff(
    session_id: Annotated[str, Field(description="Session ID to diff")],
) -> dict:
    """Show files created, modified, and deleted in a session. Returns a diff summary with file paths and change types."""  # noqa: E501

    client = get_client()
    err = await _ensure(client)
    if err:
        return err
    try:
        diff = await client.get_session_diff(session_id)
    except Exception as e:
        return {"success": False, "message": f"Diff failed: {e}", "data": {}}
    return {
        "success": True,
        "message": f"Session {session_id} diff retrieved",
        "data": {"diff": diff},
    }


async def opencode_get_messages(
    session_id: Annotated[str, Field(description="Session ID to retrieve messages from")],
    limit: Annotated[int, Field(description="Maximum number of messages to retrieve")] = 50,
) -> dict:
    """Retrieve message history from an opencode session. Returns the conversation transcript between the user and the agent."""  # noqa: E501

    client = get_client()
    err = await _ensure(client)
    if err:
        return err
    messages = await client.get_messages(session_id, limit=limit)
    return {
        "success": True,
        "message": f"Retrieved {len(messages)} messages",
        "data": {"messages": messages},
    }
