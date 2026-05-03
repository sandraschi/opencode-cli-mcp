import asyncio
from typing import Annotated, Literal

from pydantic import Field

from opencode_cli_mcp.client import OPENCODE_BINARY
from opencode_cli_mcp.job_store import create_job, get_job, run_agent_background


async def opencode_run_agent(
    prompt: Annotated[str, Field(description="The prompt/message to send to the opencode agent")],
    project: Annotated[str | None, Field(description="Project directory path (optional)")] = None,
    format: Annotated[Literal["text", "json"], Field(description="Output format: 'text' or 'json'")] = "text",  # noqa: E501
    wait: Annotated[bool, Field(description="Wait for completion (true) or return immediately with job_id (false)")] = False,  # noqa: E501
    timeout: Annotated[int, Field(description="Max seconds to wait when wait=true (default 300)")] = 300,  # noqa: E501
) -> dict:
    """Run an opencode agent with a prompt. Launches as background job; returns job_id for polling. Set wait=true to block until done."""  # noqa: E501

    if format not in ("text", "json"):
        return {"success": False, "message": f"Invalid format '{format}': must be 'text' or 'json'", "data": {}}  # noqa: E501

    cmd = [OPENCODE_BINARY, "run", prompt, "--format", format]
    if project:
        cmd.extend(["--project", project])

    job_id = await create_job(prompt, project)

    if not wait:
        asyncio.create_task(run_agent_background(job_id, cmd, timeout=timeout))
        return {
            "success": True,
            "message": "Agent started in background",
            "data": {
                "job_id": job_id,
                "prompt": prompt,
                "status": "running",
                "timeout": timeout,
            },
        }

    await run_agent_background(job_id, cmd, timeout=timeout)
    job = await get_job(job_id)
    if not job:
        return {"success": False, "message": "Job not found", "data": {}}

    return {
        "success": job["status"] == "completed",
        "message": f"Agent {job['status']}",
        "data": {
            "job_id": job_id,
            "status": job["status"],
            "stdout": job["stdout"],
            "stderr": job["stderr"],
            "exit_code": job["exit_code"],
            "error": job.get("error"),
        },
    }
