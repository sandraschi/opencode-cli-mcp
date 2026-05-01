from typing import Annotated

from pydantic import Field

from opencode_cli_mcp.client import OpencodeClient


async def opencode_list_sessions() -> dict:
    """List all active and recent opencode sessions."""  # noqa: E501

    client = OpencodeClient()
    try:
        sessions = await client.list_sessions()
        return {
            "success": True,
            "message": f"Found {len(sessions)} sessions",
            "data": {"sessions": sessions},
        }
    finally:
        await client.close()


async def opencode_get_session(
    session_id: Annotated[str, Field(description="Session ID to retrieve")],
) -> dict:
    """Get detailed information about a specific opencode session, including its metadata and state."""  # noqa: E501

    client = OpencodeClient()
    try:
        session = await client.get_session(session_id)
        return {
            "success": True,
            "message": f"Retrieved session {session_id}",
            "data": {"session": session},
        }
    finally:
        await client.close()


async def opencode_export_session(
    session_id: Annotated[str, Field(description="Session ID to export")],
) -> dict:
    """Export an opencode session as JSON. Useful for saving session transcripts for analysis or archiving."""  # noqa: E501

    client = OpencodeClient()
    try:
        data = await client.export_session(session_id)
        return {
            "success": True,
            "message": f"Exported session {session_id}",
            "data": {"export": data},
        }
    finally:
        await client.close()


async def opencode_send_message(
    session_id: Annotated[str, Field(description="Session ID to send message to")],
    message: Annotated[str, Field(description="Message text to send to the agent")],
) -> dict:
    """Send a message to an existing opencode session. Use this to continue a conversation with a running agent."""  # noqa: E501

    client = OpencodeClient()
    try:
        result = await client.send_message(session_id, message)
        return {
            "success": True,
            "message": "Message sent to session",
            "data": {"result": result},
        }
    finally:
        await client.close()


async def opencode_get_messages(
    session_id: Annotated[str, Field(description="Session ID to retrieve messages from")],
    limit: Annotated[int, Field(description="Maximum number of messages to retrieve")] = 50,
) -> dict:
    """Retrieve message history from an opencode session. Returns the conversation transcript between the user and the agent."""  # noqa: E501

    client = OpencodeClient()
    try:
        messages = await client.get_messages(session_id, limit=limit)
        return {
            "success": True,
            "message": f"Retrieved {len(messages)} messages",
            "data": {"messages": messages},
        }
    finally:
        await client.close()
