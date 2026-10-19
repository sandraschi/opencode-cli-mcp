"""Sidecar favourites store: stars, tags, notes for depot sessions.

Why a separate database instead of columns on ``opencode.db``? The depot is a
READ-ONLY consumer of opencode's database (see :mod:`opencode_cli_mcp.depot`).
opencode owns that schema and can reshape it on any upgrade; user curation
(stars, tags, notes) is OUR data and must survive those upgrades. Keeping it in
a small SQLite file next to the share pages costs nothing and removes an entire
class of "upgrade ate my favourites" failure.

Default location: ``~/.local/share/opencode-cli-mcp/meta.db`` (override with
``OPENCODE_CLI_MCP_META_DB``). WAL is enabled so the webapp can read while a
tool call writes.
"""

import os
import sqlite3
from collections.abc import Iterable
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

META_DB_ENV = "OPENCODE_CLI_MCP_META_DB"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS session_meta (
    session_id TEXT PRIMARY KEY,
    starred    INTEGER NOT NULL DEFAULT 0,
    note       TEXT,
    updated_ms INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS session_tag (
    session_id TEXT NOT NULL,
    tag        TEXT NOT NULL,
    PRIMARY KEY (session_id, tag)
);
CREATE INDEX IF NOT EXISTS idx_session_tag_tag ON session_tag(tag);
CREATE INDEX IF NOT EXISTS idx_session_meta_starred ON session_meta(starred);
"""


def meta_db_path() -> Path:
    """Sidecar DB path. Env override wins (tests use it)."""
    env = os.environ.get(META_DB_ENV)
    if env:
        return Path(env)
    return Path.home() / ".local" / "share" / "opencode-cli-mcp" / "meta.db"


@contextmanager
def _connect(path: Path | None = None):
    db = path or meta_db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now_ms() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


def _norm_tag(tag: str) -> str:
    """Lowercase, trim, and collapse whitespace so "Neuro Biology" == "neuro biology"."""
    return " ".join(tag.strip().lower().split())


def set_star(session_id: str, starred: bool = True, *, db_path: Path | None = None) -> dict[str, Any]:
    """Star or unstar a session. Idempotent."""
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT INTO session_meta (session_id, starred, updated_ms) VALUES (?,?,?) "
            "ON CONFLICT(session_id) DO UPDATE SET starred=excluded.starred, updated_ms=excluded.updated_ms",
            (session_id, 1 if starred else 0, _now_ms()),
        )
    return {"session_id": session_id, "starred": bool(starred)}


def add_tags(session_id: str, tags: Iterable[str], *, db_path: Path | None = None) -> dict[str, Any]:
    """Attach one or more tags. Blank entries are ignored."""
    cleaned = [t for t in (_norm_tag(t) for t in tags) if t]
    with _connect(db_path) as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO session_tag (session_id, tag) VALUES (?,?)",
            [(session_id, t) for t in cleaned],
        )
        conn.execute(
            "INSERT INTO session_meta (session_id, starred, updated_ms) VALUES (?,0,?) "
            "ON CONFLICT(session_id) DO UPDATE SET updated_ms=excluded.updated_ms",
            (session_id, _now_ms()),
        )
    return {"session_id": session_id, "added": cleaned, "tags": get(session_id, db_path=db_path)["tags"]}


def remove_tags(session_id: str, tags: Iterable[str], *, db_path: Path | None = None) -> dict[str, Any]:
    """Detach tags. Unknown tags are a no-op."""
    cleaned = [t for t in (_norm_tag(t) for t in tags) if t]
    with _connect(db_path) as conn:
        conn.executemany(
            "DELETE FROM session_tag WHERE session_id=? AND tag=?",
            [(session_id, t) for t in cleaned],
        )
    return {"session_id": session_id, "removed": cleaned, "tags": get(session_id, db_path=db_path)["tags"]}


def get(session_id: str, *, db_path: Path | None = None) -> dict[str, Any]:
    """Stars + tags for one session (empty defaults when unknown)."""
    with _connect(db_path) as conn:
        row = conn.execute("SELECT starred, note FROM session_meta WHERE session_id=?", (session_id,)).fetchone()
        tags = [
            r["tag"]
            for r in conn.execute(
                "SELECT tag FROM session_tag WHERE session_id=? ORDER BY tag", (session_id,)
            ).fetchall()
        ]
    return {
        "session_id": session_id,
        "starred": bool(row["starred"]) if row else False,
        "note": (row["note"] or "") if row else "",
        "tags": tags,
    }


def get_many(session_ids: Iterable[str], *, db_path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Bulk lookup for list enrichment. One query pair, not N+1."""
    ids = list(dict.fromkeys(session_ids))
    if not ids:
        return {}
    placeholders = ",".join("?" * len(ids))
    out: dict[str, dict[str, Any]] = {sid: {"session_id": sid, "starred": False, "note": "", "tags": []} for sid in ids}
    with _connect(db_path) as conn:
        for row in conn.execute(
            f"SELECT session_id, starred, note FROM session_meta WHERE session_id IN ({placeholders})", ids
        ).fetchall():
            out[row["session_id"]]["starred"] = bool(row["starred"])
            out[row["session_id"]]["note"] = row["note"] or ""
        for row in conn.execute(
            f"SELECT session_id, tag FROM session_tag WHERE session_id IN ({placeholders}) ORDER BY tag", ids
        ).fetchall():
            out[row["session_id"]]["tags"].append(row["tag"])
    return out


def session_ids(*, starred: bool | None = None, tag: str | None = None, db_path: Path | None = None) -> list[str]:
    """Session ids matching the curation filters (intersection when combined).

    ``starred=None`` means "no star constraint"; ``tag=None`` means no tag
    constraint. A starred=True + tag="x" query requires BOTH.
    """
    clauses: list[str] = []
    params: list[Any] = []
    if starred is True:
        clauses.append("session_id IN (SELECT session_id FROM session_meta WHERE starred=1)")
    if tag:
        clauses.append("session_id IN (SELECT session_id FROM session_tag WHERE tag=?)")
        params.append(_norm_tag(tag))
    if not clauses:
        return []
    # Union is the base set: a starred session may have no tags, a tagged one
    # may be unstarred - selecting from either table alone would drop half.
    sql = (
        "SELECT session_id FROM ("
        "SELECT session_id FROM session_meta UNION SELECT session_id FROM session_tag"
        f") WHERE {' AND '.join(f'({c})' for c in clauses)}"
    )
    with _connect(db_path) as conn:
        return [r["session_id"] for r in conn.execute(sql, params).fetchall()]


def tags_with_counts(*, db_path: Path | None = None) -> list[dict[str, Any]]:
    """All tags with usage counts, most used first."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT tag, COUNT(*) AS count FROM session_tag GROUP BY tag ORDER BY count DESC, tag"
        ).fetchall()
    return [{"tag": r["tag"], "count": r["count"]} for r in rows]


def stats(*, db_path: Path | None = None) -> dict[str, Any]:
    """Favourite counts for dashboards."""
    with _connect(db_path) as conn:
        starred = conn.execute("SELECT COUNT(*) AS c FROM session_meta WHERE starred=1").fetchone()["c"]
        tagged = conn.execute("SELECT COUNT(DISTINCT session_id) AS c FROM session_tag").fetchone()["c"]
        tags = conn.execute("SELECT COUNT(DISTINCT tag) AS c FROM session_tag").fetchone()["c"]
    return {"starred": starred, "tagged_sessions": tagged, "distinct_tags": tags, "db_path": str(meta_db_path())}
