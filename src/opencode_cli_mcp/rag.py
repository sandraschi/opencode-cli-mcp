"""LanceDB semantic search over the opencode session depot.

Fleet reference: arxiv-mcp ``services/vector_rag.py`` — LanceDB + FastEmbed
with ``BAAI/bge-small-en-v1.5`` (384-dim) as the default embedding model.

Optional deps: ``lancedb``, ``fastembed``, ``pyarrow`` (``uv sync --extra
rag``). Keyword search (SQLite LIKE / FTS5) keeps working without them.

Index model:

- Rows are per-session text chunks: session id, title, agent, directory,
  chunk index, body, vector, updated timestamp.
- Indexing is session-incremental: sessions newer than the last indexed
  ``time_updated`` are processed (delete-then-add per session, so a
  re-index never duplicates rows). Progress is tracked in module state for
  the webapp status bar; the last-indexed watermark persists to a small
  ``meta.json`` next to the LanceDB directory.

Env:
- ``OPENCODE_CLI_MCP_RAG_ENABLED`` (default 1)
- ``OPENCODE_CLI_MCP_EMBEDDING_MODEL`` (default ``BAAI/bge-small-en-v1.5``)
- ``OPENCODE_CLI_MCP_LANCE_DIR`` (default ``%LOCALAPPDATA%\\opencode-cli-mcp\\lancedb``)
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any

from opencode_cli_mcp.depot import default_db_path

logger = logging.getLogger(__name__)

TABLE_NAME = "session_chunks"
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 120
MAX_PART_CHARS = 8000
_EMBED_BATCH = 32


class RAGUnavailableError(Exception):
    """Raised when optional RAG dependencies are missing or indexing failed."""


def _enabled() -> bool:
    return os.environ.get("OPENCODE_CLI_MCP_RAG_ENABLED", "1").lower() not in ("0", "false", "no")


def _embedding_model() -> str:
    return os.environ.get("OPENCODE_CLI_MCP_EMBEDDING_MODEL", DEFAULT_MODEL)


def _lance_dir() -> Path:
    env = os.environ.get("OPENCODE_CLI_MCP_LANCE_DIR")
    if env:
        path = Path(env)
    else:
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        path = Path(base) / "opencode-cli-mcp" / "lancedb"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _meta_path() -> Path:
    return _lance_dir() / "meta.json"


def _load_meta() -> dict[str, Any]:
    try:
        return json.loads(_meta_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_meta(meta: dict[str, Any]) -> None:
    tmp = _meta_path().with_suffix(".json.tmp")
    tmp.write_text(json.dumps(meta), encoding="utf-8")
    tmp.replace(_meta_path())


def rag_deps_available() -> bool:
    try:
        import importlib.util as _util

        return all(_util.find_spec(m) is not None for m in ("lancedb", "fastembed", "pyarrow"))
    except ImportError:
        return False


_EMBEDDER: Any = None
_embed_lock = threading.Lock()


def _get_embedder():
    global _EMBEDDER
    if _EMBEDDER is None:
        with _embed_lock:
            if _EMBEDDER is None:
                from fastembed import TextEmbedding

                cache_dir = _lance_dir().parent / "cache" / "fastembed"
                cache_dir.mkdir(parents=True, exist_ok=True)
                _EMBEDDER = TextEmbedding(model_name=_embedding_model(), cache_dir=str(cache_dir))
                logger.info("[rag] embedder ready: %s", _embedding_model())
    return _EMBEDDER


def _encode_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    embedder = _get_embedder()
    out: list[list[float]] = []
    for start in range(0, len(texts), _EMBED_BATCH):
        out.extend([list(v) for v in embedder.embed(texts[start : start + _EMBED_BATCH])])
    return out


def _open_db():
    import lancedb

    return lancedb.connect(str(_lance_dir()))


def _open_table():
    db = _open_db()
    try:
        return db.open_table(TABLE_NAME)
    except Exception:
        return None


def _split_chunks(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks on word boundaries."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    words = text.split(" ")
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end >= len(words):
            break
        start = max(start, end - overlap)
    return chunks


# --- background indexing state -------------------------------------------

_index_state: dict[str, Any] = {}
_state_lock = threading.Lock()


def _set_state(**kw: Any) -> None:
    with _state_lock:
        _index_state.update(kw)


def index_state() -> dict[str, Any]:
    with _state_lock:
        return dict(_index_state)


def _collect_session_texts(conn: sqlite3.Connection, session_id: str, title: str) -> list[str]:
    """Collect text-part bodies for one session (cap each part, skip empty)."""
    rows = conn.execute(
        """
        SELECT p.data FROM part p
        WHERE p.session_id = ?
          AND json_extract(p.data, '$.type') = 'text'
        ORDER BY p.time_created ASC
        LIMIT 2000
        """,
        (session_id,),
    ).fetchall()
    out: list[str] = []
    for (data,) in rows:
        try:
            body = json.loads(data).get("text", "")
        except (json.JSONDecodeError, AttributeError):
            continue
        body = (body or "").strip()
        if body:
            out.append(body[:MAX_PART_CHARS])
    return out


def _index_sessions(sessions: list[dict[str, Any]], conn: sqlite3.Connection) -> int:
    """Embed and upsert chunks for the given sessions. Returns chunk count."""
    import pyarrow as pa

    rows: list[dict[str, Any]] = []
    for s in sessions:
        texts = _collect_session_texts(conn, s["id"], s.get("title") or s.get("id") or "")
        if not texts:
            continue
        chunks: list[str] = []
        for t in texts:
            chunks.extend(_split_chunks(t))
        if not chunks:
            continue
        vectors = _encode_texts(chunks)
        for idx, (body, vec) in enumerate(zip(chunks, vectors, strict=True)):
            rows.append(
                {
                    "chunk_id": f"{s['id']}:{idx}",
                    "session_id": s["id"],
                    "title": (s.get("title") or s["id"])[:500],
                    "agent": s.get("agent") or "",
                    "directory": s.get("directory") or "",
                    "chunk_idx": idx,
                    "body": body[:4000],
                    "vector": vec,
                    "updated_ms": int(s.get("time_updated") or 0),
                }
            )

    if not rows:
        return 0

    db = _open_db()
    table = _open_table()
    batch = pa.Table.from_pylist(rows)
    if table is None:
        db.create_table(TABLE_NAME, batch)
    else:
        table.add(batch)
    return len(rows)


def index_new_sessions(limit_sessions: int | None = None, batch_size: int = 50) -> dict[str, Any]:
    """Index depot sessions beyond the watermark. Runs synchronously.

    First run (watermark 0) walks newest-first so recent sessions become
    searchable immediately; subsequent runs pick up only sessions newer
    than the watermark (ASC). Call from a background task for progress.
    """
    if not _enabled():
        return {"success": False, "error": "rag_disabled"}
    if not rag_deps_available():
        return {"success": False, "error": "deps_missing", "install_hint": "uv sync --extra rag"}

    meta = _load_meta()
    watermark = int(meta.get("last_session_updated_ms", 0))
    model = meta.get("model")
    if model and model != _embedding_model():
        # Model changed since last index - start over so embeddings are consistent.
        logger.info("[rag] embedding model changed (%s -> %s); dropping table", model, _embedding_model())
        db = _open_db()
        try:
            db.drop_table(TABLE_NAME)
        except Exception:
            pass
        watermark = 0

    db_path = default_db_path()
    if not db_path.exists():
        return {"success": False, "error": f"depot not found at {db_path}"}

    _set_state(running=True, indexed_sessions=0, indexed_chunks=0, total_sessions=None, error=None)
    try:
        conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            total = conn.execute("SELECT COUNT(*) FROM session WHERE time_updated > ?", (watermark,)).fetchone()[0]
            if limit_sessions is not None:
                total = min(total, limit_sessions)
            _set_state(total_sessions=total)
            if total == 0:
                return {"success": True, "indexed_sessions": 0, "indexed_chunks": 0, "message": "up to date"}

            first_run = watermark == 0
            cursor = None  # first-run DESC boundary (exclusive)
            seen_max = watermark
            done_sessions = 0
            done_chunks = 0
            while True:
                remaining = (limit_sessions - done_sessions) if limit_sessions is not None else None
                batch = min(batch_size, remaining) if remaining is not None else batch_size
                if batch <= 0:
                    break
                if first_run:
                    rows = conn.execute(
                        """
                        SELECT id, title, agent, directory, time_updated FROM session
                        WHERE (? IS NULL OR time_updated < ?)
                        ORDER BY time_updated DESC LIMIT ?
                        """,
                        (cursor, cursor, batch),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT id, title, agent, directory, time_updated FROM session
                        WHERE time_updated > ? ORDER BY time_updated ASC LIMIT ?
                        """,
                        (watermark, batch),
                    ).fetchall()
                if not rows:
                    break
                sessions = [dict(r) for r in rows]
                done_chunks += _index_sessions(sessions, conn)
                done_sessions += len(sessions)
                if first_run:
                    cursor = min(int(s["time_updated"] or 0) for s in sessions)
                    seen_max = max(seen_max, max(int(s["time_updated"] or 0) for s in sessions))
                else:
                    watermark = max(int(s["time_updated"] or 0) for s in sessions)
                _set_state(indexed_sessions=done_sessions, indexed_chunks=done_chunks)
            last_ts = seen_max if first_run else watermark
        finally:
            conn.close()

        meta["last_session_updated_ms"] = last_ts
        meta["model"] = _embedding_model()
        _save_meta(meta)
        _set_state(running=False, indexed_sessions=done_sessions, indexed_chunks=done_chunks, done=True)
        return {"success": True, "indexed_sessions": done_sessions, "indexed_chunks": done_chunks}
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("[rag] index failed")
        _set_state(running=False, error=str(exc))
        return {"success": False, "error": str(exc)}


def reset_index() -> None:
    """Drop the vector table and clear the watermark (full re-index)."""
    db = _open_db()
    try:
        db.drop_table(TABLE_NAME)
    except Exception:
        pass
    try:
        _meta_path().unlink(missing_ok=True)
    except OSError:
        pass
    _set_state(running=False, indexed_sessions=0, indexed_chunks=0, total_sessions=None, error=None, done=False)


def rag_status() -> dict[str, Any]:
    if not _enabled():
        return {"available": False, "enabled": False, "reason": "rag_disabled"}
    if not rag_deps_available():
        return {
            "available": False,
            "enabled": True,
            "model": _embedding_model(),
            "install_hint": "uv sync --extra rag",
            "indexed_chunks": 0,
        }
    table = _open_table()
    count = 0
    if table is not None:
        try:
            count = int(table.count_rows())
        except Exception:
            count = 0
    meta = _load_meta()
    state = index_state()
    pending = None
    if state.get("total_sessions") is not None:
        pending = max(0, int(state["total_sessions"]) - int(state.get("indexed_sessions", 0)))
    return {
        "available": True,
        "enabled": True,
        "backend": "fastembed",
        "model": _embedding_model(),
        "db_path": str(_lance_dir()),
        "indexed_chunks": count,
        "last_watermark_ms": meta.get("last_session_updated_ms"),
        "running": bool(state.get("running")),
        "indexed_sessions": state.get("indexed_sessions"),
        "total_sessions": state.get("total_sessions"),
        "pending_sessions": pending,
        "error": state.get("error"),
    }


def semantic_search(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Semantic search over indexed session chunks."""
    if not _enabled():
        raise RAGUnavailableError("Semantic search disabled (OPENCODE_CLI_MCP_RAG_ENABLED=0)")
    if not rag_deps_available():
        raise RAGUnavailableError("Install RAG deps: uv sync --extra rag")

    table = _open_table()
    if table is None:
        return []

    q = query.strip()
    if not q:
        return []

    qvec = _encode_texts([q])[0]
    raw = table.search(qvec).limit(limit).to_list()
    hits: list[dict[str, Any]] = []
    for row in raw:
        distance = float(row.get("_distance", 0.0))
        similarity = 1.0 / (1.0 + distance)
        body = str(row.get("body", ""))
        snippet = body[:300] + ("..." if len(body) > 300 else "")
        hits.append(
            {
                "session_id": row.get("session_id", ""),
                "title": str(row.get("title", "")),
                "agent": str(row.get("agent", "")),
                "directory": str(row.get("directory", "")),
                "snippet": snippet,
                "rank": round(similarity, 4),
                "distance": round(distance, 4),
                "engine": "lancedb",
            }
        )
    return hits
