from typing import Annotated

from pydantic import Field

from opencode_cli_mcp.job_store import cancel_job, get_job, list_jobs


async def opencode_get_run_status(
    job_id: Annotated[str, Field(description="Job ID from opencode_run_agent")],
) -> dict:
    """Poll the status of a background agent run. Returns stdout/stderr accumulated so far, status, and exit code."""  # noqa: E501

    job = await get_job(job_id)
    if not job:
        return {"success": False, "message": f"Job '{job_id}' not found", "data": {}}

    return {
        "success": True,
        "message": f"Job {job['status']}",
        "data": {
            "job_id": job_id,
            "status": job["status"],
            "stdout": job["stdout"],
            "stderr": job["stderr"],
            "exit_code": job["exit_code"],
            "error": job.get("error"),
            "created_at": job["created_at"],
            "completed_at": job["completed_at"],
        },
    }


async def opencode_list_runs(
    limit: Annotated[int, Field(description="Max jobs to return", ge=1, le=100)] = 20,
) -> dict:
    """List all recent agent runs with their status and exit codes."""  # noqa: E501

    jobs = await list_jobs(limit=limit)
    return {
        "success": True,
        "message": f"Found {len(jobs)} runs",
        "data": {
            "runs": [
                {
                    "job_id": j["job_id"],
                    "prompt": j["prompt"],
                    "status": j["status"],
                    "exit_code": j["exit_code"],
                    "created_at": j["created_at"],
                    "completed_at": j["completed_at"],
                }
                for j in jobs
            ]
        },
    }


async def opencode_cancel_run(
    job_id: Annotated[str, Field(description="Job ID to cancel")],
) -> dict:
    """Cancel a running or queued agent run."""  # noqa: E501

    ok = await cancel_job(job_id)
    if not ok:
        return {"success": False, "message": f"Cannot cancel job '{job_id}' (not running or not found)", "data": {}}  # noqa: E501
    return {"success": True, "message": f"Cancelled job '{job_id}'", "data": {"job_id": job_id}}
