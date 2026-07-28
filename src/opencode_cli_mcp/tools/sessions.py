import html
from datetime import UTC, datetime
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


def _msg_role(msg: dict) -> str:
    parts = msg.get("parts", msg.get("content", []))
    if isinstance(parts, list):
        for p in parts:
            if isinstance(p, dict) and p.get("type") == "text":
                return p.get("text", "")
        return ""
    return str(parts) if parts else ""


def _msg_ts(msg: dict) -> str:
    ts = msg.get("createdAt") or msg.get("timestamp") or ""
    if ts and isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    return str(ts) if ts else ""


async def opencode_session_grep(
    query: Annotated[str, Field(description="Text to search for in session messages")],
    session_limit: Annotated[int, Field(description="Max sessions to search", ge=1, le=200)] = 50,
    max_messages: Annotated[int, Field(description="Max messages to fetch per session", ge=1, le=500)] = 100,
) -> dict:
    """Search across all opencode sessions for a text string in messages.

    Returns sessions with matching message excerpts.
    """
    client = get_client()
    err = await _ensure(client)
    if err:
        return err

    sessions = await client.list_sessions()
    query_lower = query.lower()
    matches = []

    for sess in (sessions or [])[:session_limit]:
        sid = sess.get("id") or sess.get("session_id")
        if not sid:
            continue
        try:
            messages = await client.get_messages(sid, limit=max_messages)
        except Exception:
            continue
        sess_matches = []
        for msg in messages or []:
            text = _msg_role(msg)
            if query_lower in text.lower():
                snippet = text[:300] + "..." if len(text) > 300 else text
                sess_matches.append(
                    {
                        "role": msg.get("role", "unknown"),
                        "ts": _msg_ts(msg),
                        "snippet": snippet,
                    }
                )
        if sess_matches:
            matches.append(
                {
                    "session_id": sid,
                    "title": sess.get("title") or sess.get("name", ""),
                    "created_at": sess.get("createdAt", ""),
                    "matches": sess_matches[:10],
                    "match_count": len(sess_matches),
                }
            )

    return {
        "success": True,
        "message": f"Searched {min(len(sessions or []), session_limit)} sessions, found matches in {len(matches)}",
        "data": {
            "query": query,
            "results": matches,
            "total_sessions_searched": min(len(sessions or []), session_limit),
            "sessions_with_matches": len(matches),
        },
    }


async def opencode_export_session(
    session_id: Annotated[str, Field(description="Session ID to export")],
    format: Annotated[str, Field(description="Export format: markdown or html")] = "markdown",
    max_messages: Annotated[int, Field(description="Max messages to export", ge=1, le=1000)] = 200,
) -> dict:
    """Export an opencode session transcript as markdown or HTML."""
    client = get_client()
    err = await _ensure(client)
    if err:
        return err

    session = await client.get_session(session_id)
    messages = await client.get_messages(session_id, limit=max_messages)

    title = session.get("title") or session.get("name") or f"opencode-session-{session_id[:8]}"

    if format == "html":
        ts = _msg_ts(session)
        lines = [
            "<!DOCTYPE html>",
            '<html><head><meta charset="utf-8">',
            f"<title>{html.escape(str(title))}</title>",
            "<style>",
            "body{max-width:800px;margin:2em auto;padding:0 1em;"
            "font:14px/1.6 system-ui;color:#e2e8f0;background:#0f172a}",
            "h1{color:#f59e0b}",
            ".msg{margin:1em 0;padding:1em;border-radius:8px}",
            ".user{background:#1e293b}",
            ".assistant{background:#1e293b;border-left:3px solid #f59e0b}",
            ".ts{color:#64748b;font-size:12px}",
            "pre{background:#020617;padding:1em;border-radius:4px;overflow-x:auto}",
            "code{font:13px/1.5 'JetBrains Mono',monospace}",
            "</style></head><body>",
            f"<h1>{html.escape(str(title))}</h1>",
            f"<p class='ts'>Session {html.escape(session_id)}</p>",
        ]
        for msg in messages or []:
            role = msg.get("role", "unknown")
            text = html.escape(_msg_role(msg))
            ts = html.escape(_msg_ts(msg))
            lines.append(f"<div class='msg {role}'>")
            lines.append(f"  <p class='ts'>{role} &mdash; {ts}</p>")
            lines.append(f"  <pre>{text}</pre>" if "\n" in text else f"  <p>{text}</p>")
            lines.append("</div>")
        lines.append("</body></html>")
        output = "\n".join(lines)
        ext = "html"
    else:
        lines = [
            f"# {title}",
            "",
            f"Session: {session_id}",
            "",
            "---",
            "",
        ]
        for msg in messages or []:
            role = msg.get("role", "unknown")
            text = _msg_role(msg)
            ts = _msg_ts(msg)
            lines.append(f"## {role}")
            if ts:
                lines.append(f"*{ts}*")
            lines.append("")
            lines.append(text)
            lines.append("")
            lines.append("---")
            lines.append("")
        output = "\n".join(lines)
        ext = "md"

    return {
        "success": True,
        "message": f"Exported session {session_id} as {format} ({len(output)} chars)",
        "data": {
            "session_id": session_id,
            "title": title,
            "format": format,
            "output": output,
            "message_count": len(messages or []),
            "filename": f"{title}.{ext}",
        },
    }
