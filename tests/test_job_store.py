import asyncio
import time

import pytest

from opencode_cli_mcp import job_store


@pytest.fixture(autouse=True)
def _reset_job_store():
    job_store._jobs.clear()
    yield
    job_store._jobs.clear()


@pytest.mark.asyncio
async def test_create_job():
    jid = await job_store.create_job("test prompt", None)
    assert len(jid) == 12
    job = await job_store.get_job(jid)
    assert job is not None
    assert job["prompt"] == "test prompt"
    assert job["status"] == "queued"
    assert job["exit_code"] is None
    assert job["stdout"] == ""
    assert job["stderr"] == ""
    assert job["project"] is None


@pytest.mark.asyncio
async def test_create_job_with_project():
    jid = await job_store.create_job("build", "D:/repos/test")
    job = await job_store.get_job(jid)
    assert job["project"] == "D:/repos/test"


@pytest.mark.asyncio
async def test_get_job_not_found():
    assert await job_store.get_job("nonexistent") is None


@pytest.mark.asyncio
async def test_list_jobs_empty():
    jobs = await job_store.list_jobs()
    assert jobs == []


@pytest.mark.asyncio
async def test_list_jobs_ordering():
    jid1 = await job_store.create_job("first", None)
    await asyncio.sleep(0.01)
    jid2 = await job_store.create_job("second", None)
    jobs = await job_store.list_jobs()
    assert len(jobs) == 2
    assert jobs[0]["job_id"] == jid2
    assert jobs[1]["job_id"] == jid1


@pytest.mark.asyncio
async def test_list_jobs_limit():
    for i in range(10):
        await job_store.create_job(f"prompt {i}", None)
    jobs = await job_store.list_jobs(limit=3)
    assert len(jobs) == 3


@pytest.mark.asyncio
async def test_update_job_status():
    jid = await job_store.create_job("test", None)
    await job_store.update_job(jid, status="running")
    job = await job_store.get_job(jid)
    assert job["status"] == "running"
    assert job["completed_at"] is None


@pytest.mark.asyncio
async def test_update_job_completion():
    jid = await job_store.create_job("test", None)
    await job_store.update_job(jid, status="completed", exit_code=0)
    job = await job_store.get_job(jid)
    assert job["status"] == "completed"
    assert job["exit_code"] == 0
    assert job["completed_at"] is not None


@pytest.mark.asyncio
async def test_update_job_failed():
    jid = await job_store.create_job("test", None)
    await job_store.update_job(jid, status="failed", exit_code=1, error="broken")
    job = await job_store.get_job(jid)
    assert job["status"] == "failed"
    assert job["exit_code"] == 1
    assert job["error"] == "broken"
    assert job["completed_at"] is not None


@pytest.mark.asyncio
async def test_update_job_nonexistent():
    await job_store.update_job("nope", status="completed")


@pytest.mark.asyncio
async def test_append_output():
    jid = await job_store.create_job("test", None)
    await job_store.append_output(jid, "stdout", "line1\n")
    await job_store.append_output(jid, "stdout", "line2\n")
    await job_store.append_output(jid, "stderr", "error\n")
    job = await job_store.get_job(jid)
    assert job["stdout"] == "line1\nline2\n"
    assert job["stderr"] == "error\n"


@pytest.mark.asyncio
async def test_append_output_nonexistent():
    await job_store.append_output("nope", "stdout", "text")


@pytest.mark.asyncio
async def test_cancel_job_running():
    jid = await job_store.create_job("test", None)
    await job_store.update_job(jid, status="running")
    ok = await job_store.cancel_job(jid)
    assert ok is True
    job = await job_store.get_job(jid)
    assert job["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_job_queued():
    jid = await job_store.create_job("test", None)
    ok = await job_store.cancel_job(jid)
    assert ok is True
    job = await job_store.get_job(jid)
    assert job["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_job_already_completed():
    jid = await job_store.create_job("test", None)
    await job_store.update_job(jid, status="completed", exit_code=0)
    ok = await job_store.cancel_job(jid)
    assert ok is False


@pytest.mark.asyncio
async def test_cancel_job_nonexistent():
    assert await job_store.cancel_job("nope") is False


@pytest.mark.asyncio
async def test_cleanup_old_jobs():
    for i in range(60):
        jid = await job_store.create_job(f"prompt {i}", None)
        await job_store.update_job(jid, status="completed", exit_code=0)
    await job_store._cleanup_old_jobs()
    jobs = await job_store.list_jobs(limit=100)
    assert len(jobs) == 50


@pytest.mark.asyncio
async def test_cleanup_preserves_running():
    await job_store.create_job("running job", None)
    for i in range(51):
        jid = await job_store.create_job(f"done {i}", None)
        await job_store.update_job(jid, status="completed", exit_code=0)
    await job_store._cleanup_old_jobs()
    jobs = await job_store.list_jobs(limit=100)
    running = [j for j in jobs if j["status"] == "queued"]
    assert len(running) == 1


@pytest.mark.asyncio
async def test_get_job_excludes_process():
    jid = await job_store.create_job("test", None)
    job_store._jobs[jid]["_process"] = "fake-process"
    job = await job_store.get_job(jid)
    assert "_process" not in job


@pytest.mark.asyncio
async def test_concurrent_job_creation():
    async def create_one(i: int) -> str:
        return await job_store.create_job(f"concurrent {i}", None)

    results = await asyncio.gather(*[create_one(i) for i in range(20)])
    assert len(set(results)) == 20
    jobs = await job_store.list_jobs(limit=30)
    assert len(jobs) == 20


@pytest.mark.asyncio
async def test_set_process():
    jid = await job_store.create_job("test", None)

    class FakeProcess:
        pass

    proc = FakeProcess()
    await job_store.set_process(jid, proc)
    assert job_store._jobs[jid]["_process"] is proc


@pytest.mark.asyncio
async def test_set_process_nonexistent():
    await job_store.set_process("nope", object())


def test_remove_stuck_jobs_recent():
    jid = job_store._create_sync("recent", None)
    job_store._jobs[jid]["status"] = "running"
    job_store._remove_stuck_jobs()
    assert jid in job_store._jobs


def test_remove_stuck_jobs_old():
    jid = job_store._create_sync("old", None)
    job_store._jobs[jid]["status"] = "running"
    job_store._jobs[jid]["created_at"] = time.time() - 7200
    job_store._remove_stuck_jobs()
    assert jid not in job_store._jobs


def _create_sync(prompt, project):
    import uuid

    jid = uuid.uuid4().hex[:12]
    job_store._jobs[jid] = {
        "job_id": jid,
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
    return jid


job_store._create_sync = _create_sync
