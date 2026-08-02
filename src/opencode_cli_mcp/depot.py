"""Direct SQLite access to the opencode session depot.

The opencode serve HTTP API (client.py) is the live-interaction surface: it
can list, read, message, diff, and export sessions, but it has no
archive/unarchive/rename/delete/stats, and it dies when ``opencode serve``
is not running. The SQLite database opencode writes (``opencode.db``) is the
full source of truth and works offline.

Safety model:

- Reads use a read-only URI connection (``mode=ro``) - it is impossible to
  corrupt the depot through a query.
- Writes are narrow: only the ``session`` table columns ``time_archived``
  and ``title`` are ever modified. ``message``/``part``/``session_message``
  rows are never touched directly; deletes rely on the schema's ON DELETE
  CASCADE foreign keys.
- All writes use WAL-friendly short transactions with a busy timeout so
  concurrent opencode access does not deadlock.
"""

import json
import os
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

# Overridable so tests and exotic installs can point elsewhere.
DB_PATH_ENV = "OPENCODE_DB_PATH"

# Current USD-per-1M-token prices for restating the stale `cost` column.
# The stored cost was computed at session time with older pricing data and
# overcounts cache reads (~2.5x for deepseek-v4-flash). Restate on read with
# the live models.json rates. Keyed by model id from session.model JSON.
_MODEL_PRICES: dict[str, tuple[float, float, float, float]] = {
    # (input, output, reasoning, cache_read) per 1M tokens
    "deepseek-v4-flash": (0.14, 0.28, 0.28, 0.0028),
    "deepseek-v4-pro": (0.435, 0.87, 0.87, 0.003625),
    "deepseek-chat": (0.14, 0.28, 0.28, 0.0028),
    "deepseek-reasoner": (0.14, 0.28, 0.28, 0.0028),
}


def _model_id(model_json: Any) -> str | None:
    """Extract the model id from session.model (JSON string or plain)."""
    if not model_json:
        return None
    if isinstance(model_json, str):
        try:
            data = json.loads(model_json)
            if isinstance(data, dict) and data.get("id"):
                return str(data["id"])
        except json.JSONDecodeError:
            return model_json.strip() or None
    elif isinstance(model_json, dict) and model_json.get("id"):
        return str(model_json["id"])
    return None


def _cost_from_parts(model_id: str | None, t_in: float, t_out: float, t_reason: float, t_cache: float) -> float | None:
    """Cost at current base rates for a model's token buckets. None when unpriceable."""
    prices = _MODEL_PRICES.get(model_id) if model_id else None
    if prices is None:
        return None
    p_in, p_out, p_reason, p_cache = prices
    return round((t_in * p_in + t_out * p_out + t_reason * p_reason + t_cache * p_cache) / 1_000_000, 4)


def _restate_cost(row: Any) -> float | None:
    """Estimate session cost at current pricing. None when unpriceable."""
    model_id = _model_id(row["model"])
    return _cost_from_parts(
        model_id,
        row["tokens_input"] or 0,
        row["tokens_output"] or 0,
        row["tokens_reasoning"] or 0,
        row["tokens_cache_read"] or 0,
    )


# Columns we map from the session table into depot dicts.
_SESSION_COLUMNS = [
    "id",
    "project_id",
    "parent_id",
    "slug",
    "directory",
    "title",
    "version",
    "share_url",
    "summary_additions",
    "summary_deletions",
    "summary_files",
    "time_created",
    "time_updated",
    "time_compacting",
    "time_archived",
    "workspace_id",
    "path",
    "agent",
    "model",
    "cost",
    "tokens_input",
    "tokens_output",
    "tokens_reasoning",
    "tokens_cache_read",
    "tokens_cache_write",
]


class DepotError(Exception):
    """Raised when the opencode depot cannot be opened or is corrupt."""


def default_db_path() -> Path:
    """Locate opencode.db. Env override wins, then XDG data home, then ~/.local/share."""
    env = os.environ.get(DB_PATH_ENV)
    if env:
        return Path(env)
    data_home = os.environ.get("XDG_DATA_HOME")
    if data_home:
        return Path(data_home) / "opencode" / "opencode.db"
    return Path.home() / ".local" / "share" / "opencode" / "opencode.db"


def _connect(db_path: Path | None = None, read_only: bool = True) -> sqlite3.Connection:
    path = Path(db_path) if db_path else default_db_path()
    if not path.exists():
        raise DepotError(f"opencode depot not found at {path} - run opencode once to create it")
    if read_only:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    if not read_only:
        # Without this, ON DELETE CASCADE is a no-op (SQLite default is OFF).
        conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _fmt_ts(ms: int | None) -> str | None:
    if not ms:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    except (OverflowError, OSError, ValueError):
        return None


def _row_to_session(row: sqlite3.Row) -> dict[str, Any]:
    s: dict[str, Any] = {}
    for col in _SESSION_COLUMNS:
        s[col] = row[col]
    s["archived"] = row["time_archived"] is not None
    s["time_created_display"] = _fmt_ts(row["time_created"])
    s["time_updated_display"] = _fmt_ts(row["time_updated"])
    s["time_archived_display"] = _fmt_ts(row["time_archived"])
    s["cost_est"] = _restate_cost(row)
    return s


def list_sessions(
    *,
    status: str = "all",
    project: str | None = None,
    agent: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort: str = "updated",
    timeframe_days: int | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """List sessions from the depot with filters. Returns page + totals.

    ``timeframe_days`` restricts to sessions updated within the last N days
    (for "what did I work on 3 weeks ago" style browsing).
    """
    clauses: list[str] = []
    params: list[Any] = []
    if status == "active":
        clauses.append("time_archived IS NULL")
    elif status == "archived":
        clauses.append("time_archived IS NOT NULL")
    if project:
        clauses.append("(directory LIKE ? OR project_id LIKE ?)")
        params.extend([f"%{project}%", f"%{project}%"])
    if agent:
        clauses.append("agent = ?")
        params.append(agent)
    if search:
        clauses.append("title LIKE ?")
        params.append(f"%{search}%")
    if timeframe_days and timeframe_days > 0:
        clauses.append("time_updated > ?")
        params.append(int(datetime.now(UTC).timestamp() * 1000) - timeframe_days * 86_400_000)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    order = {
        "updated": "time_updated DESC",
        "created": "time_created DESC",
        "archived": "time_archived DESC",
        "cost": "cost DESC",
        "tokens": "tokens_input + tokens_output DESC",
        "title": "title ASC",
    }.get(sort, "time_updated DESC")

    conn = _connect(db_path, read_only=True)
    try:
        total = conn.execute(f"SELECT COUNT(*) FROM session {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM session {where} ORDER BY {order} LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
    finally:
        conn.close()

    sessions = [_row_to_session(r) for r in rows]
    return {
        "sessions": sessions,
        "total": total,
        "limit": limit,
        "offset": offset,
        "next_offset": offset + limit if offset + limit < total else None,
    }


def get_session(session_id: str, *, db_path: Path | None = None) -> dict[str, Any] | None:
    """Full session record plus message/part counts."""
    conn = _connect(db_path, read_only=True)
    try:
        row = conn.execute("SELECT * FROM session WHERE id = ?", (session_id,)).fetchone()
        if row is None:
            return None
        session = _row_to_session(row)
        session["message_count"] = conn.execute(
            "SELECT COUNT(*) FROM message WHERE session_id = ?", (session_id,)
        ).fetchone()[0]
        session["part_count"] = conn.execute(
            "SELECT COUNT(*) FROM part WHERE session_id = ?", (session_id,)
        ).fetchone()[0]
        return session
    finally:
        conn.close()


def get_session_transcript(session_id: str, *, limit: int = 200, db_path: Path | None = None) -> list[dict[str, Any]]:
    """Text parts of a session with roles and timestamps, oldest first.

    Reads straight from opencode.db (message.data carries role + time) so it
    works offline, unlike the live serve-API transcript. Used by the Depot
    page detail view.
    """
    conn = _connect(db_path, read_only=True)
    try:
        rows = conn.execute(
            """
            SELECT json_extract(m.data, '$.role') AS role,
                   json_extract(m.data, '$.time.created') AS ts_ms,
                   json_extract(p.data, '$.text') AS text
            FROM part p
            JOIN message m ON p.message_id = m.id
            WHERE p.session_id = ? AND json_extract(p.data, '$.type') = 'text'
            ORDER BY p.time_created ASC
            LIMIT ?
            """,
            (session_id, max(1, min(limit, 1000))),
        ).fetchall()
        out = []
        for role, ts_ms, text in rows:
            if not text or not str(text).strip():
                continue
            out.append({"role": role or "unknown", "ts": ts_ms, "text": str(text)})
        return out
    finally:
        conn.close()


def search_transcripts(
    query: str,
    *,
    limit: int = 20,
    include_archived: bool = True,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Full-text search across message parts (JSON $.text) and session titles.

    Uses SQLite LIKE on json_extract - FTS5 is overkill for a single-user
    depot and LIKE is fast enough at this scale (thousands of sessions).
    """
    conn = _connect(db_path, read_only=True)
    try:
        archived_clause = "" if include_archived else "AND s.time_archived IS NULL"
        rows = conn.execute(
            f"""
            SELECT s.id AS session_id, s.title, s.time_archived, s.directory, s.agent,
                   p.data AS part_data, p.time_created AS part_ts
            FROM part p
            JOIN session s ON s.id = p.session_id
            WHERE (json_extract(p.data, '$.type') = 'text'
                   AND json_extract(p.data, '$.text') LIKE ?)
                  {archived_clause}
            ORDER BY p.time_created DESC
            LIMIT ?
            """,
            [f"%{query}%", limit],
        ).fetchall()

        results = []
        for r in rows:
            text = ""
            try:
                text = json.loads(r["part_data"]).get("text", "")
            except (json.JSONDecodeError, AttributeError):
                text = ""
            snippet = text[:300] + "..." if len(text) > 300 else text
            results.append(
                {
                    "session_id": r["session_id"],
                    "title": r["title"],
                    "archived": r["time_archived"] is not None,
                    "directory": r["directory"],
                    "agent": r["agent"],
                    "timestamp": _fmt_ts(r["part_ts"]),
                    "snippet": snippet,
                }
            )
        return {"results": results, "count": len(results), "query": query}
    finally:
        conn.close()


def archive_session(session_id: str, *, db_path: Path | None = None) -> bool:
    """Set time_archived to now. Returns True if a row was updated."""
    return _update_session(session_id, {"time_archived": int(datetime.now(UTC).timestamp() * 1000)}, db_path)


def unarchive_session(session_id: str, *, db_path: Path | None = None) -> bool:
    """Clear time_archived - the feature opencode's UI is missing."""
    return _update_session(session_id, {"time_archived": None}, db_path)


def rename_session(session_id: str, title: str, *, db_path: Path | None = None) -> bool:
    """Update the session title."""
    return _update_session(session_id, {"title": title}, db_path)


def delete_session(session_id: str, *, db_path: Path | None = None) -> bool:
    """Delete a session; messages/parts/diffs cascade via FK. Permanent."""
    conn = _connect(db_path, read_only=False)
    try:
        cur = conn.execute("DELETE FROM session WHERE id = ?", (session_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def _update_session(session_id: str, fields: dict[str, Any], db_path: Path | None) -> bool:
    if not fields:
        return False
    conn = _connect(db_path, read_only=False)
    try:
        cols = ", ".join(f"{k} = ?" for k in fields)
        cur = conn.execute(f"UPDATE session SET {cols} WHERE id = ?", [*fields.values(), session_id])
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def depot_stats(*, db_path: Path | None = None) -> dict[str, Any]:
    """Aggregate stats across the whole depot."""
    conn = _connect(db_path, read_only=True)
    try:
        totals = conn.execute(
            """
            SELECT COUNT(*) AS total,
                   SUM(CASE WHEN time_archived IS NOT NULL THEN 1 ELSE 0 END) AS archived,
                   SUM(CASE WHEN time_archived IS NULL THEN 1 ELSE 0 END) AS active,
                   COALESCE(SUM(cost), 0) AS total_cost,
                   COALESCE(SUM(tokens_input), 0) AS tokens_input,
                   COALESCE(SUM(tokens_output), 0) AS tokens_output,
                   COALESCE(SUM(tokens_reasoning), 0) AS tokens_reasoning,
                   COALESCE(SUM(tokens_cache_read), 0) AS tokens_cache_read
            FROM session
            """
        ).fetchone()

        by_agent = conn.execute(
            """
            SELECT COALESCE(agent, 'unknown') AS agent, COUNT(*) AS count,
                   COALESCE(SUM(cost), 0) AS cost,
                   COALESCE(SUM(tokens_input), 0) AS tokens_input,
                   COALESCE(SUM(tokens_output), 0) AS tokens_output,
                   COALESCE(SUM(tokens_reasoning), 0) AS tokens_reasoning,
                   COALESCE(SUM(tokens_cache_read), 0) AS tokens_cache_read,
                   MIN(model) AS model
            FROM session GROUP BY agent ORDER BY count DESC LIMIT 10
            """
        ).fetchall()

        by_project = conn.execute(
            """
            SELECT project_id, COUNT(*) AS count, COALESCE(SUM(cost), 0) AS cost,
                   COALESCE(SUM(tokens_input), 0) AS tokens_input,
                   COALESCE(SUM(tokens_output), 0) AS tokens_output,
                   COALESCE(SUM(tokens_reasoning), 0) AS tokens_reasoning,
                   COALESCE(SUM(tokens_cache_read), 0) AS tokens_cache_read,
                   MIN(model) AS model
            FROM session GROUP BY project_id ORDER BY count DESC LIMIT 10
            """
        ).fetchall()

        top_cost = conn.execute(
            """
            SELECT id, title, cost, model, tokens_input, tokens_output,
                   tokens_reasoning, tokens_cache_read
            FROM session ORDER BY cost DESC LIMIT 5
            """
        ).fetchall()

        all_cost_rows = conn.execute(
            "SELECT model, cost, tokens_input, tokens_output, tokens_reasoning, tokens_cache_read FROM session"
        ).fetchall()
        est_total = 0.0
        est_known = 0
        for r in all_cost_rows:
            est = _restate_cost(r)
            if est is not None:
                est_total += est
                est_known += 1

        def _est_for_row(r: sqlite3.Row) -> float:
            est = _restate_cost(r)
            return est if est is not None else round(r["cost"] or 0, 4)

        db_path_resolved = db_path or default_db_path()
        db_size = db_path_resolved.stat().st_size if db_path_resolved.exists() else 0
        messages = conn.execute("SELECT COUNT(*) FROM message").fetchone()[0]
        parts = conn.execute("SELECT COUNT(*) FROM part").fetchone()[0]
        part_types = {
            str(r[0]): r[1]
            for r in conn.execute(
                "SELECT json_extract(data, '$.type') AS t, COUNT(*) AS c FROM part GROUP BY t ORDER BY c DESC LIMIT 8"
            ).fetchall()
        }
        last_updated = conn.execute("SELECT MAX(time_updated) FROM session").fetchone()[0]

        return {
            "totals": {
                "total": totals["total"],
                "archived": totals["archived"] or 0,
                "active": totals["active"] or 0,
                "total_cost": round(totals["total_cost"] or 0, 4),
                "estimated_cost": round(est_total, 2),
                "estimated_cost_known_sessions": est_known,
                "tokens_input": totals["tokens_input"] or 0,
                "tokens_output": totals["tokens_output"] or 0,
                "tokens_reasoning": totals["tokens_reasoning"] or 0,
                "tokens_cache_read": totals["tokens_cache_read"] or 0,
            },
            "db": {
                "path": str(db_path_resolved),
                "size_bytes": db_size,
                "messages": messages,
                "parts": parts,
                "part_types": part_types,
                "last_updated_ms": last_updated,
            },
            "by_agent": [{**dict(r), "cost_est": _est_for_row(r)} for r in by_agent],
            "by_project": [{**dict(r), "cost_est": _est_for_row(r)} for r in by_project],
            "top_cost": [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "cost": round(r["cost"] or 0, 4),
                    "cost_est": _est_for_row(r),
                }
                for r in top_cost
            ],
        }
    finally:
        conn.close()


def usage_series(*, days: int = 30, db_path: Path | None = None) -> dict[str, Any]:
    """Daily buckets of tokens + cost from assistant messages.

    Time source is the message's own ``time.created`` (provider usage arrives
    per completion). Cost comes in two flavors: ``cost_stored`` (what opencode
    recorded at message time, variant pricing included) and ``cost_est``
    (restated at current base rates; only summed for priceable models, see
    ``cost_est_known``). Gap days are filled with zero buckets so charts
    render continuously.
    """
    conn = _connect(db_path, read_only=True)
    try:
        cutoff_ms = int(datetime.now(UTC).timestamp() * 1000) - days * 86_400_000
        rows = conn.execute(
            """
            SELECT json_extract(data, '$.modelID') AS model_id,
                   json_extract(data, '$.tokens.input') AS t_in,
                   json_extract(data, '$.tokens.output') AS t_out,
                   json_extract(data, '$.tokens.reasoning') AS t_reason,
                   json_extract(data, '$.tokens.cache.read') AS t_cache,
                   json_extract(data, '$.tokens.cache.write') AS t_cache_w,
                   json_extract(data, '$.cost') AS cost,
                   json_extract(data, '$.time.created') AS ts
            FROM message
            WHERE json_extract(data, '$.role') = 'assistant'
              AND json_extract(data, '$.tokens.input') IS NOT NULL
              AND json_extract(data, '$.time.created') >= ?
            """,
            (cutoff_ms,),
        ).fetchall()

        raw: dict[str, dict[str, Any]] = {}
        for model_id, t_in, t_out, t_reason, t_cache, t_cache_w, cost, ts in rows:
            if not ts:
                continue
            day = datetime.fromtimestamp(int(ts) / 1000, tz=UTC).strftime("%Y-%m-%d")
            b = raw.setdefault(
                day,
                {
                    "messages": 0,
                    "tokens_input": 0,
                    "tokens_output": 0,
                    "tokens_reasoning": 0,
                    "tokens_cache_read": 0,
                    "tokens_cache_write": 0,
                    "cost_stored": 0.0,
                    "cost_est": 0.0,
                    "cost_est_known": 0,
                },
            )
            b["messages"] += 1
            b["tokens_input"] += t_in or 0
            b["tokens_output"] += t_out or 0
            b["tokens_reasoning"] += t_reason or 0
            b["tokens_cache_read"] += t_cache or 0
            b["tokens_cache_write"] += t_cache_w or 0
            b["cost_stored"] += cost or 0
            est = _cost_from_parts(model_id, t_in or 0, t_out or 0, t_reason or 0, t_cache or 0)
            if est is not None:
                b["cost_est"] += est
                b["cost_est_known"] += 1

        # Fill gap days so charts are continuous.
        if raw:
            first = min(raw)
            last = max(raw)
            cursor = datetime.strptime(first, "%Y-%m-%d")
            end = datetime.strptime(last, "%Y-%m-%d")
            while cursor < end:
                key = cursor.strftime("%Y-%m-%d")
                raw.setdefault(
                    key,
                    {
                        "messages": 0,
                        "tokens_input": 0,
                        "tokens_output": 0,
                        "tokens_reasoning": 0,
                        "tokens_cache_read": 0,
                        "tokens_cache_write": 0,
                        "cost_stored": 0.0,
                        "cost_est": 0.0,
                        "cost_est_known": 0,
                    },
                )
                cursor += timedelta(days=1)

        buckets = [{"day": day, **raw[day]} for day in sorted(raw)]
        totals = {
            "messages": sum(b["messages"] for b in buckets),
            "tokens_input": sum(b["tokens_input"] for b in buckets),
            "tokens_output": sum(b["tokens_output"] for b in buckets),
            "tokens_reasoning": sum(b["tokens_reasoning"] for b in buckets),
            "tokens_cache_read": sum(b["tokens_cache_read"] for b in buckets),
            "tokens_cache_write": sum(b["tokens_cache_write"] for b in buckets),
            "cost_stored": round(sum(b["cost_stored"] for b in buckets), 4),
            "cost_est": round(sum(b["cost_est"] for b in buckets), 4),
        }
        return {"days": days, "buckets": buckets, "totals": totals}
    finally:
        conn.close()
