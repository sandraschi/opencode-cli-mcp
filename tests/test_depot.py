"""Tests for the opencode_depot portmanteau + SQLite depot layer.

Builds a throwaway opencode.db (matching the real schema) and points
depot functions at it via OPENCODE_DB_PATH. Never touches the real
~/.local/share/opencode/opencode.db.
"""

import json
import os
import sqlite3
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from opencode_cli_mcp import depot
from opencode_cli_mcp.tools.depot import opencode_depot

SCHEMA = """
CREATE TABLE session (
    id text PRIMARY KEY,
    project_id text NOT NULL,
    parent_id text,
    slug text NOT NULL,
    directory text NOT NULL,
    title text NOT NULL,
    version text NOT NULL,
    share_url text,
    summary_additions integer,
    summary_deletions integer,
    summary_files integer,
    summary_diffs text,
    revert text,
    permission text,
    time_created integer NOT NULL,
    time_updated integer NOT NULL,
    time_compacting integer,
    time_archived integer,
    workspace_id text, path text, agent text, model text,
    cost real DEFAULT 0 NOT NULL,
    tokens_input integer DEFAULT 0 NOT NULL,
    tokens_output integer DEFAULT 0 NOT NULL,
    tokens_reasoning integer DEFAULT 0 NOT NULL,
    tokens_cache_read integer DEFAULT 0 NOT NULL,
    tokens_cache_write integer DEFAULT 0 NOT NULL,
    metadata text
);
CREATE TABLE message (
    id text PRIMARY KEY,
    session_id text NOT NULL,
    time_created integer NOT NULL,
    time_updated integer NOT NULL,
    data text NOT NULL,
    FOREIGN KEY (session_id) REFERENCES session(id) ON DELETE CASCADE
);
CREATE TABLE part (
    id text PRIMARY KEY,
    message_id text NOT NULL,
    session_id text NOT NULL,
    time_created integer NOT NULL,
    time_updated integer NOT NULL,
    data text NOT NULL,
    FOREIGN KEY (message_id) REFERENCES message(id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES session(id) ON DELETE CASCADE
);
"""


@pytest.fixture()
def depot_db(tmp_path: Path):
    db_path = tmp_path / "opencode.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    now = int(datetime.now(UTC).timestamp() * 1000)
    archived = now - 86_400_000  # one day ago

    conn.execute(
        "INSERT INTO session (id, project_id, slug, directory, title, version, time_created, time_updated, "
        "time_archived, agent, model, cost, tokens_input, tokens_output) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "sess_active",
            "proj_a",
            "s1",
            r"D:\Dev\repos\opencode-cli-mcp",
            "Active session",
            "1.0.0",
            now - 3_600_000,
            now - 600_000,
            None,
            "build",
            "deepseek-v4-flash",
            0.05,
            1000,
            500,
        ),
    )
    conn.execute(
        "INSERT INTO session (id, project_id, slug, directory, title, version, time_created, time_updated, "
        "time_archived, agent, model, cost, tokens_input, tokens_output) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "sess_arch",
            "proj_a",
            "s2",
            r"D:\Dev\repos\arxiv-mcp",
            "Archived session",
            "1.0.0",
            now - 172_800_000,
            now - 172_800_000,
            archived,
            "research",
            "qwen3:14b",
            0.2,
            5000,
            2000,
        ),
    )
    conn.execute(
        "INSERT INTO message (id, session_id, time_created, time_updated, data) VALUES (?,?,?,?,?)",
        ("msg1", "sess_active", now, now, json.dumps({"role": "user"})),
    )
    conn.execute(
        "INSERT INTO part (id, message_id, session_id, time_created, time_updated, data) VALUES (?,?,?,?,?,?)",
        (
            "part1",
            "msg1",
            "sess_active",
            now,
            now,
            json.dumps({"type": "text", "text": "Reduce 4090 power limit discussion"}),
        ),
    )
    conn.commit()
    conn.close()

    os.environ["OPENCODE_DB_PATH"] = str(db_path)
    yield db_path
    os.environ.pop("OPENCODE_DB_PATH", None)


# --- depot layer ---


def test_list_all(depot_db):
    page = depot.list_sessions()
    assert page["total"] == 2
    assert {s["id"] for s in page["sessions"]} == {"sess_active", "sess_arch"}


def test_list_status_filter(depot_db):
    active = depot.list_sessions(status="active")
    assert active["total"] == 1
    assert active["sessions"][0]["id"] == "sess_active"
    archived = depot.list_sessions(status="archived")
    assert archived["total"] == 1
    assert archived["sessions"][0]["id"] == "sess_arch"
    assert archived["sessions"][0]["archived"] is True


def test_list_project_filter(depot_db):
    page = depot.list_sessions(project="arxiv")
    assert page["total"] == 1
    assert page["sessions"][0]["id"] == "sess_arch"


def test_list_agent_filter(depot_db):
    page = depot.list_sessions(agent="build")
    assert page["total"] == 1
    assert page["sessions"][0]["id"] == "sess_active"


def test_list_pagination(depot_db):
    page = depot.list_sessions(limit=1, offset=0)
    assert len(page["sessions"]) == 1
    assert page["next_offset"] == 1
    page2 = depot.list_sessions(limit=1, offset=1)
    assert page2["next_offset"] is None


def test_get_session(depot_db):
    s = depot.get_session("sess_active")
    assert s is not None
    assert s["title"] == "Active session"
    assert s["message_count"] == 1
    assert s["part_count"] == 1
    assert depot.get_session("missing") is None


def test_search_transcripts(depot_db):
    result = depot.search_transcripts("4090")
    assert result["count"] == 1
    assert result["results"][0]["session_id"] == "sess_active"
    assert "4090" in result["results"][0]["snippet"]
    assert depot.search_transcripts("nonexistent")["count"] == 0


def test_archive_unarchive(depot_db):
    assert depot.archive_session("sess_active")
    active = depot.get_session("sess_active")
    assert active is not None
    assert active["archived"] is True
    assert depot.unarchive_session("sess_active")
    active = depot.get_session("sess_active")
    assert active is not None
    assert active["archived"] is False


def test_archive_missing(depot_db):
    assert depot.archive_session("missing") is False


def test_rename(depot_db):
    assert depot.rename_session("sess_active", "New title")
    renamed = depot.get_session("sess_active")
    assert renamed is not None
    assert renamed["title"] == "New title"


def test_delete_cascades(depot_db):
    conn = sqlite3.connect(depot_db)
    assert conn.execute("SELECT COUNT(*) FROM message WHERE session_id='sess_active'").fetchone()[0] == 1
    conn.close()

    assert depot.delete_session("sess_active")
    conn = sqlite3.connect(depot_db)
    assert conn.execute("SELECT COUNT(*) FROM session WHERE id='sess_active'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM message WHERE session_id='sess_active'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM part WHERE session_id='sess_active'").fetchone()[0] == 0
    conn.close()


def test_stats(depot_db):
    stats = depot.depot_stats()
    assert stats["totals"]["total"] == 2
    assert stats["totals"]["archived"] == 1
    assert stats["totals"]["active"] == 1
    assert stats["totals"]["total_cost"] == pytest.approx(0.25)
    agents = {a["agent"]: a["count"] for a in stats["by_agent"]}
    assert agents == {"build": 1, "research": 1}


def test_missing_db():
    os.environ["OPENCODE_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "nope.db")
    try:
        with pytest.raises(depot.DepotError):
            depot.list_sessions()
    finally:
        os.environ.pop("OPENCODE_DB_PATH", None)


# --- portmanteau tool ---


@pytest.mark.asyncio()
async def test_tool_list(depot_db):
    result = await opencode_depot(action="list", status="all")
    assert result["success"] is True
    assert result["data"]["total"] == 2


@pytest.mark.asyncio()
async def test_tool_get(depot_db):
    result = await opencode_depot(action="get", session_id="sess_active")
    assert result["success"] is True
    assert result["data"]["session"]["message_count"] == 1


@pytest.mark.asyncio()
async def test_tool_unarchive_roundtrip(depot_db):
    result = await opencode_depot(action="unarchive", session_id="sess_arch")
    assert result["success"] is True
    restored = depot.get_session("sess_arch")
    assert restored is not None
    assert restored["archived"] is False
    result2 = await opencode_depot(action="archive", session_id="sess_arch")
    assert result2["success"] is True


@pytest.mark.asyncio()
async def test_tool_rename(depot_db):
    result = await opencode_depot(action="rename", session_id="sess_active", title="Renamed")
    assert result["success"] is True
    renamed = depot.get_session("sess_active")
    assert renamed is not None
    assert renamed["title"] == "Renamed"


@pytest.mark.asyncio()
async def test_tool_delete(depot_db):
    result = await opencode_depot(action="delete", session_id="sess_arch")
    assert result["success"] is True
    assert depot.get_session("sess_arch") is None


@pytest.mark.asyncio()
async def test_tool_search(depot_db):
    result = await opencode_depot(action="search", query="4090")
    assert result["success"] is True
    assert result["data"]["count"] == 1


@pytest.mark.asyncio()
async def test_tool_stats(depot_db):
    result = await opencode_depot(action="stats")
    assert result["success"] is True
    assert result["data"]["totals"]["total"] == 2


@pytest.mark.asyncio()
async def test_tool_missing_session(depot_db):
    result = await opencode_depot(action="get", session_id="nope")
    assert result["success"] is False
    assert "not found" in result["message"]


@pytest.mark.asyncio()
async def test_tool_missing_param(depot_db):
    result = await opencode_depot(action="search")
    assert result["success"] is False
    assert "requires" in result["message"]


@pytest.mark.asyncio()
async def test_tool_missing_db():
    os.environ["OPENCODE_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "nope.db")
    try:
        result = await opencode_depot(action="list")
        assert result["success"] is False
        assert "not found" in result["message"]
    finally:
        os.environ.pop("OPENCODE_DB_PATH", None)


async def test_tool_rag_requires_query():
    from opencode_cli_mcp.tools.depot import opencode_depot

    result = await opencode_depot(action="rag")
    assert result["success"] is False
    assert "query" in result["message"]


async def test_tool_rag_status_and_search(monkeypatch):
    """RAG actions dispatch to the rag module (availability-agnostic)."""
    from unittest.mock import MagicMock

    from opencode_cli_mcp import rag as rag_mod
    from opencode_cli_mcp.tools.depot import opencode_depot

    fake_status = {"enabled": True, "indexed_sessions": 3, "running": False}
    fake_hits = [{"session_id": "s1", "score": 0.91, "snippet": "santa claus plan"}]

    monkeypatch.setattr(rag_mod, "semantic_search", MagicMock(return_value=fake_hits))
    monkeypatch.setattr(rag_mod, "index_new_sessions", MagicMock(return_value={"indexed": 3}))
    monkeypatch.setattr(rag_mod, "rag_status", MagicMock(return_value=fake_status))

    status = await opencode_depot(action="rag_status")
    assert status["success"] and status["data"]["enabled"] is True

    hits = await opencode_depot(action="rag", query="the santa plan")
    assert hits["success"] and len(hits["data"]["results"]) == 1

    idx = await opencode_depot(action="rag_index")
    assert idx["success"] and idx["data"]["indexed"] == 3


async def test_tool_rag_unavailable_surfaces_error(monkeypatch):
    from opencode_cli_mcp import rag as rag_mod
    from opencode_cli_mcp.tools.depot import opencode_depot

    def _raise(q, limit=20):
        raise rag_mod.RAGUnavailableError("Install RAG deps: uv sync --extra rag")

    monkeypatch.setattr(rag_mod, "semantic_search", _raise)
    result = await opencode_depot(action="rag", query="anything")
    assert result["success"] is False
    assert "RAG deps" in result["message"]
