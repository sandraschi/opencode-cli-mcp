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
        }
    return job_id


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
        return _jobs.get(job_id)


async def list_jobs(limit: int = 20) -> list[dict[str, Any]]:
    async with _lock:
        sorted_jobs = sorted(
            _jobs.values(), key=lambda j: j["created_at"], reverse=True
        )
        return sorted_jobs[:limit]


async def cancel_job(job_id: str) -> bool:
    async with _lock:
        job = _jobs.get(job_id)
        if not job or job["status"] not in ("running", "queued"):
            return False
        job["status"] = "cancelled"
        job["completed_at"] = time.time()
    return True


async def _cleanup_old_jobs():
    """Remove oldest completed jobs when over limit."""
    async with _lock:
        completed = [(jid, j) for jid, j in _jobs.items() if j["status"] in ("completed", "failed", "cancelled")]  # noqa: E501
        if len(completed) > _MAX_COMPLETED:
            completed.sort(key=lambda x: x[1]["completed_at"] or 0)
            for jid, _ in completed[: len(completed) - _MAX_COMPLETED]:
                del _jobs[jid]


async def run_agent_background(
    job_id: str,
    cmd: list[str],
):
    await update_job(job_id, status="running")
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async def _reader(stream: asyncio.StreamReader, stream_name: str):
            while True:
                line = await stream.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace")
                await append_output(job_id, stream_name, text)

        await asyncio.gather(
            _reader(proc.stdout, "stdout"),
            _reader(proc.stderr, "stderr"),
        )
        await proc.wait()

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
        await _cleanup_old_jobs()
