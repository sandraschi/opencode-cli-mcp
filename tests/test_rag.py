"""RAG index tests: incremental watermark, delete-then-add (no duplicates), reset.

Uses a throwaway opencode.db (real schema subset) + a temp LanceDB dir and
patches embedding so no model download happens. Skipped when the optional
rag extras (lancedb/fastembed/pyarrow) are not installed.
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

pytest.importorskip("lancedb")
pytest.importorskip("fastembed")
pytest.importorskip("pyarrow")

from opencode_cli_mcp import rag  # noqa: E402

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

DIM = 384


def _fake_encode(texts: list[str]) -> list[list[float]]:
    """Deterministic pseudo-vectors - indexing/delete logic only, no model."""
    out = []
    for t in texts:
        seed = sum(ord(c) for c in t)
        out.append([float((seed + i) % 7) / 7.0 for i in range(DIM)])
    return out


LONG_TEXT = (
    "In December we decided to build santiclaus-mcp and scope the elf coordination layer. " * 250
)  # ~2750 words -> several chunks
LONG_TEXT_2 = "And then we agreed the reindeer scheduling API should be JSON over SSE. " * 250


def _add_text_part(conn, session_id: str, text: str, ts: int, idx: int) -> None:
    import json

    conn.execute(
        "INSERT INTO part (id, message_id, session_id, time_created, time_updated, data) VALUES (?,?,?,?,?,?)",
        (
            f"part_{session_id}_{idx}",
            f"msg_{session_id}_{idx}",
            session_id,
            ts,
            ts,
            json.dumps({"type": "text", "text": text}),
        ),
    )


@pytest.fixture()
def rag_env(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "opencode.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    now = int(datetime.now(UTC).timestamp() * 1000)
    conn.execute(
        "INSERT INTO session (id, project_id, slug, directory, title, version, "
        "time_created, time_updated, agent) VALUES (?,?,?,?,?,?,?,?,?)",
        ("ses_rag_1", "proj", "slug", str(tmp_path), "Santa Claus MCP Plan", "1", now, now, "claude"),
    )
    _add_text_part(conn, "ses_rag_1", LONG_TEXT, now, 1)
    conn.commit()
    conn.close()

    monkeypatch.setenv("OPENCODE_DB_PATH", str(db_path))
    monkeypatch.setenv("OPENCODE_CLI_MCP_LANCE_DIR", str(tmp_path / "lancedb"))
    monkeypatch.setenv("OPENCODE_CLI_MCP_RAG_ENABLED", "1")
    monkeypatch.setattr(rag, "_encode_texts", _fake_encode)
    # Small chunk size so the 8000-char part cap yields several chunks.
    from functools import partial

    monkeypatch.setattr(rag, "_split_chunks", partial(rag._split_chunks, size=300, overlap=40))
    return tmp_path, db_path


def _chunk_count() -> int:
    table = rag._open_table()
    return int(table.count_rows()) if table is not None else 0


def test_index_then_reindex_no_change(rag_env):
    report = rag.index_new_sessions()
    assert report["success"] and report["indexed_sessions"] == 1
    count1 = _chunk_count()
    # Long text, but each part body is capped at MAX_PART_CHARS (8000) before
    # chunking - still several chunks at CHUNK_SIZE=1500 words.
    expected1 = len(rag._split_chunks(LONG_TEXT[: rag.MAX_PART_CHARS]))
    assert count1 == expected1, f"expected {expected1} chunks, got {count1}"
    assert count1 > 1

    report2 = rag.index_new_sessions()
    assert report2["indexed_sessions"] == 0
    assert _chunk_count() == count1  # watermark advanced, nothing re-processed


def test_reindex_updated_session_no_duplicates(rag_env):
    tmp_path, db_path = rag_env
    rag.index_new_sessions()
    count1 = _chunk_count()

    # Session gains a new message -> time_updated advances -> next index run
    # must DELETE its old chunks before re-adding, not duplicate them.
    conn = sqlite3.connect(db_path)
    now = int(datetime.now(UTC).timestamp() * 1000)
    conn.execute("UPDATE session SET time_updated = ? WHERE id = 'ses_rag_1'", (now + 1,))
    _add_text_part(conn, "ses_rag_1", LONG_TEXT_2, now, 2)
    conn.commit()
    conn.close()

    report = rag.index_new_sessions()
    assert report["success"] and report["indexed_sessions"] == 1
    count2 = _chunk_count()

    # No duplicates: chunk ids must be unique, and count must equal the sum of
    # per-part chunk counts (each part body capped at MAX_PART_CHARS), not the
    # old chunks + new chunks.
    table = rag._open_table()
    ids = [row["chunk_id"] for row in table.to_arrow().to_pylist()]
    assert len(ids) == len(set(ids)), "duplicate chunks after re-index"
    expected = len(rag._split_chunks(LONG_TEXT[: rag.MAX_PART_CHARS])) + len(
        rag._split_chunks(LONG_TEXT_2[: rag.MAX_PART_CHARS])
    )
    assert count2 == expected, f"expected {expected} unique chunks, got {count2} (was {count1})"


def test_reset_index_clears(rag_env):
    rag.index_new_sessions()
    assert _chunk_count() > 0
    rag.reset_index()
    assert _chunk_count() == 0
    st = rag.rag_status()
    assert st["available"] and st["indexed_chunks"] == 0


def test_rag_status_shape(rag_env):
    st = rag.rag_status()
    assert st["available"] is True
    assert st["model"] == rag.DEFAULT_MODEL
