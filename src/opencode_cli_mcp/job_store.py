import asyncio
import time
import uuid
from typing import Any

_jobs: dict[str, dict[str, Any]] = {}
_lock = asyncio.Lock()
_MAX_COMPLETED = 50


async def create_job(prompt: str, project: str | None) -> str:
    job_id = uuid.uuid4().hex[:12]
    async with _lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "prompt": prompt,
            "project": project,
            "status": "queued",
            "created_at": time.time(),
            "completed_at": None,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "error": None,
            "_process": None,
        }
    return job_id


async def set_process(job_id: str, proc: asyncio.subprocess.Process):
    async with _lock:
        job = _jobs.get(job_id)
        if job:
            job["_process"] = proc


async def update_job(
    job_id: str,
    *,
    status: str | None = None,
    exit_code: int | None = None,
    stdout: str | None = None,
    stderr: str | None = None,
    error: str | None = None,
):
    async with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        if status is not None:
            job["status"] = status
        if exit_code is not None:
            job["exit_code"] = exit_code
        if stdout is not None:
            job["stdout"] += stdout
        if stderr is not None:
            job["stderr"] += stderr
        if error is not None:
            job["error"] = error
        if status in ("completed", "failed", "cancelled"):
            job["completed_at"] = time.time()


async def append_output(job_id: str, stream: str, text: str):
    async with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        if stream == "stdout":
            job["stdout"] += text
        elif stream == "stderr":
            job["stderr"] += text


async def get_job(job_id: str) -> dict[str, Any] | None:
    async with _lock:
        raw = _jobs.get(job_id)
        if raw is None:
            return None
        return {k: v for k, v in raw.items() if k != "_process"}


async def list_jobs(limit: int = 20) -> list[dict[str, Any]]:
    async with _lock:
        sorted_jobs = sorted(
            _jobs.values(), key=lambda j: j["created_at"], reverse=True
        )
        return [
            {k: v for k, v in j.items() if k != "_process"}
            for j in sorted_jobs[:limit]
        ]


async def cancel_job(job_id: str) -> bool:
    async with _lock:
        job = _jobs.get(job_id)
        if not job or job["status"] not in ("running", "queued"):
            return False
        job["status"] = "cancelled"
        job["completed_at"] = time.time()
        proc = job.get("_process")
        if proc and isinstance(proc, asyncio.subprocess.Process) and proc.returncode is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
    return True


async def _cleanup_old_jobs():
    async with _lock:
        terminal = ("completed", "failed", "cancelled")
        completed = [(jid, j) for jid, j in _jobs.items() if j["status"] in terminal]
        if len(completed) > _MAX_COMPLETED:
            completed.sort(key=lambda x: x[1]["completed_at"] or 0)
            for jid, _ in completed[: len(completed) - _MAX_COMPLETED]:
                del _jobs[jid]


def _remove_stuck_jobs():
    now = time.time()
    to_remove = []
    for jid, job in list(_jobs.items()):
        if job["status"] in ("running", "queued") and (now - job["created_at"]) > 3600:
            proc = job.get("_process")
            if proc and isinstance(proc, asyncio.subprocess.Process) and proc.returncode is None:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
            to_remove.append(jid)
    for jid in to_remove:
        del _jobs[jid]


async def run_agent_background(
    job_id: str,
    cmd: list[str],
    timeout: int = 300,
):
    await update_job(job_id, status="running")
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
            msg = f"Timed out after {timeout}s"
            await update_job(job_id, status="failed", error=msg, exit_code=-1)
        else:
            await update_job(
                job_id,
                status="completed" if proc.returncode == 0 else "failed",
                exit_code=proc.returncode,
            )
    except FileNotFoundError:
        await update_job(job_id, status="failed", error="opencode binary not found")
    except Exception as e:
        await update_job(job_id, status="failed", error=str(e))
    finally:
        _remove_stuck_jobs()
        await _cleanup_old_jobs()
