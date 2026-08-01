"""Cross-process job store backed by SQLite.

The MCP stdio server (spawned by Claude Desktop) and the FastAPI backend
(uvicorn) are separate processes. The previous in-memory dict gave each
process its own empty store, so the webapp's Runs view could never show
MCP-launched runs. Jobs now live in SQLite (WAL mode) at
%LOCALAPPDATA%\\opencode-cli-mcp\\jobs.db, shared by both processes and
surviving restarts. Override with OPENCODE_CLI_MCP_JOBS_DB (tests do).

Concurrency model: one connection per process, serialized by a
threading.Lock held inside sync helpers that run via asyncio.to_thread.
Deliberately no asyncio.Lock - those bind to an event loop, which breaks
under per-test event loops. State transitions are atomic via SQL WHERE
guards, which also makes them race-safe across processes.

Process handles cannot be shared across processes: the spawning process
keeps asyncio Process handles in _procs; the child PID is persisted so the
other process can still cancel via os.kill.
"""

import asyncio
import os
import signal
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

_TERMINAL = ("completed", "failed", "cancelled")
_MAX_COMPLETED = 50
_REAP_GRACE = 600  # seconds past a job's own timeout before the reaper acts

# Strong references to fire-and-forget tasks. asyncio only keeps weak
# references; an unreferenced task can be garbage-collected mid-flight.
_background_tasks: set[asyncio.Task] = set()

# Process-local handles for subprocesses this process spawned.
_procs: dict[str, Any] = {}

_db_lock = threading.Lock()
_conn: sqlite3.Connection | None = None

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    prompt TEXT NOT NULL,
    project TEXT,
    timeout INTEGER NOT NULL DEFAULT 300,
    status TEXT NOT NULL,
    created_at REAL NOT NULL,
    completed_at REAL,
    exit_code INTEGER,
    stdout TEXT NOT NULL DEFAULT '',
    stderr TEXT NOT NULL DEFAULT '',
    error TEXT,
    proc_pid INTEGER
);
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at DESC);
"""

_COLUMNS = (
    "job_id",
    "prompt",
    "project",
    "timeout",
    "status",
    "created_at",
    "completed_at",
    "exit_code",
    "stdout",
    "stderr",
    "error",
)
_SELECT = f"SELECT {', '.join(_COLUMNS)} FROM jobs"


def _db_path() -> Path:
    override = os.environ.get("OPENCODE_CLI_MCP_JOBS_DB")
    if override:
        return Path(override)
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "opencode-cli-mcp"
    return base / "jobs.db"


def _get_conn() -> sqlite3.Connection:
    """Lazy per-process connection. Callers must hold _db_lock."""
    global _conn
    if _conn is None:
        path = _db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.executescript(_SCHEMA)
        conn.commit()
        _conn = conn
    return _conn


def _row_to_dict(row: tuple) -> dict[str, Any]:
    return dict(zip(_COLUMNS, row))


def _kill_pid(pid: int | None):
    """Best-effort cross-process kill (TerminateProcess on Windows)."""
    if not pid:
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except (OSError, ProcessLookupError, PermissionError):
        pass


def _kill_local_or_pid(job_id: str, pid: int | None):
    proc = _procs.pop(job_id, None)
    if proc is not None:
        # We own the handle - authoritative. If it already exited, do NOT
        # fall through to a PID kill (the OS may have reused the PID).
        if getattr(proc, "returncode", 0) is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        return
    _kill_pid(pid)


# ---------------------------------------------------------------------------
# sync core (runs in asyncio.to_thread)
# ---------------------------------------------------------------------------


def _sync_create(job_id: str, prompt: str, project: str | None, timeout: int):
    with _db_lock:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO jobs (job_id, prompt, project, timeout, status, created_at) VALUES (?, ?, ?, ?, 'queued', ?)",
            (job_id, prompt, project, timeout, time.time()),
        )
        conn.commit()


def _sync_update(
    job_id: str,
    status: str | None,
    exit_code: int | None,
    stdout: str | None,
    stderr: str | None,
    error: str | None,
):
    sets, params = [], []
    if status is not None:
        sets.append("status = ?")
        params.append(status)
        if status in _TERMINAL:
            sets.append("completed_at = ?")
            params.append(time.time())
    if exit_code is not None:
        sets.append("exit_code = ?")
        params.append(exit_code)
    if stdout is not None:
        sets.append("stdout = stdout || ?")
        params.append(stdout)
    if stderr is not None:
        sets.append("stderr = stderr || ?")
        params.append(stderr)
    if error is not None:
        sets.append("error = ?")
        params.append(error)
    if not sets:
        return
    params.append(job_id)
    with _db_lock:
        conn = _get_conn()
        conn.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE job_id = ?", params)
        conn.commit()


def _sync_finalize(job_id: str, status: str, exit_code: int | None, error: str | None) -> bool:
    with _db_lock:
        conn = _get_conn()
        cur = conn.execute(
            "UPDATE jobs SET status = ?, completed_at = ?,"
            " exit_code = COALESCE(?, exit_code), error = COALESCE(?, error)"
            " WHERE job_id = ? AND status NOT IN ('completed', 'failed', 'cancelled')",
            (status, time.time(), exit_code, error, job_id),
        )
        conn.commit()
        return cur.rowcount == 1


def _sync_try_mark_running(job_id: str) -> bool:
    with _db_lock:
        conn = _get_conn()
        cur = conn.execute(
            "UPDATE jobs SET status = 'running' WHERE job_id = ? AND status = 'queued'",
            (job_id,),
        )
        conn.commit()
        return cur.rowcount == 1


def _sync_set_proc_pid(job_id: str, pid: int | None):
    with _db_lock:
        conn = _get_conn()
        conn.execute("UPDATE jobs SET proc_pid = ? WHERE job_id = ?", (pid, job_id))
        conn.commit()


def _sync_get(job_id: str) -> dict[str, Any] | None:
    with _db_lock:
        conn = _get_conn()
        row = conn.execute(f"{_SELECT} WHERE job_id = ?", (job_id,)).fetchone()
    return _row_to_dict(row) if row else None


def _sync_list(limit: int, offset: int = 0) -> list[dict[str, Any]]:
    with _db_lock:
        conn = _get_conn()
        rows = conn.execute(
            f"{_SELECT} ORDER BY created_at DESC, rowid DESC LIMIT ? OFFSET ?", (limit, offset)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _sync_cancel(job_id: str) -> tuple[bool, int | None]:
    with _db_lock:
        conn = _get_conn()
        cur = conn.execute(
            "UPDATE jobs SET status = 'cancelled', completed_at = ?"
            " WHERE job_id = ? AND status IN ('running', 'queued')",
            (time.time(), job_id),
        )
        conn.commit()
        if cur.rowcount != 1:
            return (False, None)
        row = conn.execute("SELECT proc_pid FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    return (True, row[0] if row else None)


def _sync_cleanup():
    with _db_lock:
        conn = _get_conn()
        conn.execute(
            "DELETE FROM jobs WHERE status IN ('completed', 'failed', 'cancelled')"
            " AND job_id NOT IN ("
            "   SELECT job_id FROM jobs"
            "   WHERE status IN ('completed', 'failed', 'cancelled')"
            "   ORDER BY completed_at DESC, created_at DESC LIMIT ?)",
            (_MAX_COMPLETED,),
        )
        conn.commit()


def _sync_reap() -> list[tuple[str, int | None]]:
    """Mark timed-out jobs failed; return (job_id, proc_pid) for killing."""
    now = time.time()
    with _db_lock:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT job_id, proc_pid, MAX(COALESCE(timeout, 300), 1) + ? AS reap_limit"
            " FROM jobs"
            " WHERE status IN ('running', 'queued')"
            " AND (created_at + MAX(COALESCE(timeout, 300), 1) + ?) < ?",
            (_REAP_GRACE, _REAP_GRACE, now),
        ).fetchall()
        for job_id, _pid, limit in rows:
            conn.execute(
                "UPDATE jobs SET status = 'failed', completed_at = ?,"
                " error = ?, exit_code = COALESCE(exit_code, -1)"
                " WHERE job_id = ? AND status IN ('running', 'queued')",
                (now, f"reaped: exceeded {int(limit)}s without completing", job_id),
            )
        conn.commit()
    return [(jid, pid) for jid, pid, _limit in rows]


# ---------------------------------------------------------------------------
# async API (unchanged signatures)
# ---------------------------------------------------------------------------


async def create_job(prompt: str, project: str | None, timeout: int = 300) -> str:
    job_id = uuid.uuid4().hex[:12]
    await asyncio.to_thread(_sync_create, job_id, prompt, project, timeout)
    return job_id


def spawn_agent_background(job_id: str, cmd: list[str], timeout: int = 300) -> asyncio.Task:
    """Launch run_agent_background as a task and keep a strong reference."""
    task = asyncio.create_task(run_agent_background(job_id, cmd, timeout=timeout))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


async def set_process(job_id: str, proc: Any):
    _procs[job_id] = proc
    await asyncio.to_thread(_sync_set_proc_pid, job_id, getattr(proc, "pid", None))


async def update_job(
    job_id: str,
    *,
    status: str | None = None,
    exit_code: int | None = None,
    stdout: str | None = None,
    stderr: str | None = None,
    error: str | None = None,
):
    await asyncio.to_thread(_sync_update, job_id, status, exit_code, stdout, stderr, error)


async def finalize_job(
    job_id: str,
    *,
    status: str,
    exit_code: int | None = None,
    error: str | None = None,
) -> bool:
    """Set a terminal status only if the job is not already terminal.

    Prevents the completion path from overwriting a cancellation (a killed
    process exits nonzero, which previously flipped cancelled -> failed).
    Atomic via the SQL WHERE guard - also race-safe across processes.
    """
    changed = await asyncio.to_thread(_sync_finalize, job_id, status, exit_code, error)
    if changed:
        _procs.pop(job_id, None)
    return changed


async def _try_mark_running(job_id: str) -> bool:
    """Transition queued -> running atomically.

    Returns False if the job left the queued state before starting (e.g.
    cancelled while queued) so the caller never spawns the process.
    """
    return await asyncio.to_thread(_sync_try_mark_running, job_id)


async def append_output(job_id: str, stream: str, text: str):
    if stream == "stdout":
        await asyncio.to_thread(_sync_update, job_id, None, None, text, None, None)
    elif stream == "stderr":
        await asyncio.to_thread(_sync_update, job_id, None, None, None, text, None)


async def get_job(job_id: str) -> dict[str, Any] | None:
    return await asyncio.to_thread(_sync_get, job_id)


async def list_jobs(limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    return await asyncio.to_thread(_sync_list, limit, offset)


async def cancel_job(job_id: str) -> bool:
    cancelled, pid = await asyncio.to_thread(_sync_cancel, job_id)
    if cancelled:
        _kill_local_or_pid(job_id, pid)
    return cancelled


async def _cleanup_old_jobs():
    await asyncio.to_thread(_sync_cleanup)


async def _reap_stuck_jobs():
    """Kill and mark failed any job that exceeded its own timeout plus grace.

    Records are kept (marked failed) so output and status stay queryable;
    _cleanup_old_jobs prunes them later like any other terminal job. A
    process without the local handle falls back to killing by stored PID.
    """
    reaped = await asyncio.to_thread(_sync_reap)
    for job_id, pid in reaped:
        _kill_local_or_pid(job_id, pid)


async def run_agent_background(
    job_id: str,
    cmd: list[str],
    timeout: int = 300,
):
    if not await _try_mark_running(job_id):
        return  # cancelled while queued - never spawn the process
    deadline = time.monotonic() + timeout

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await set_process(job_id, proc)

        async def _reader(stream: asyncio.StreamReader, stream_name: str):
            remaining = deadline - time.monotonic()
            while remaining > 0:
                try:
                    line = await asyncio.wait_for(stream.readline(), timeout=min(remaining, 5))
                    if not line:
                        break
                    text = line.decode("utf-8", errors="replace")
                    await append_output(job_id, stream_name, text)
                except TimeoutError:
                    if time.monotonic() >= deadline:
                        break
                    remaining = deadline - time.monotonic()
                    continue
                remaining = deadline - time.monotonic()

            if remaining <= 0:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass

        # Spawned with PIPE, so both streams are guaranteed non-None; assert to
        # satisfy the type checker and fail loudly if that invariant breaks.
        assert proc.stdout is not None
        assert proc.stderr is not None
        await asyncio.gather(
            _reader(proc.stdout, "stdout"),
            _reader(proc.stderr, "stderr"),
        )
        timeout_left = max(deadline - time.monotonic(), 5)
        try:
            await asyncio.wait_for(proc.wait(), timeout=timeout_left)
        except (TimeoutError, ProcessLookupError):
            try:
                proc.kill()
            except ProcessLookupError:
                pass

        timed_out = time.monotonic() >= deadline
        if timed_out:
            await finalize_job(job_id, status="failed", error=f"Timed out after {timeout}s", exit_code=-1)
        else:
            await finalize_job(
                job_id,
                status="completed" if proc.returncode == 0 else "failed",
                exit_code=proc.returncode,
            )
    except FileNotFoundError:
        await finalize_job(job_id, status="failed", error="opencode binary not found")
    except Exception as e:
        await finalize_job(job_id, status="failed", error=str(e))
    finally:
        _procs.pop(job_id, None)
        await _reap_stuck_jobs()
        await _cleanup_old_jobs()


# ---------------------------------------------------------------------------
# test helpers (sync on purpose - callable from sync fixtures)
# ---------------------------------------------------------------------------


def _reset_state_for_tests():
    with _db_lock:
        conn = _get_conn()
        conn.execute("DELETE FROM jobs")
        conn.commit()
    _procs.clear()
    _background_tasks.clear()


def _set_created_at_for_tests(job_id: str, created_at: float):
    with _db_lock:
        conn = _get_conn()
        conn.execute("UPDATE jobs SET created_at = ? WHERE job_id = ?", (created_at, job_id))
        conn.commit()
