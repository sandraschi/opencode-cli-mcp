import os
import subprocess
from typing import Annotated, Literal

from pydantic import Field

from opencode_cli_mcp.client import OPENCODE_BINARY
from opencode_cli_mcp.job_store import (
    create_job,
    get_job,
    run_agent_background,
    spawn_agent_background,
)


async def opencode_run_agent(
    prompt: Annotated[str, Field(description="The prompt/message to send to the opencode agent")],
    project: Annotated[str | None, Field(description="Project directory path (optional)")] = None,
    format: Annotated[Literal["text", "json"], Field(description="Output format: 'text' or 'json'")] = "text",  # noqa: E501
    wait: Annotated[
        bool, Field(description="Wait for completion (true) or return immediately with job_id (false)")
    ] = False,  # noqa: E501
    timeout: Annotated[int, Field(description="Max seconds to wait when wait=true (default 300)")] = 300,  # noqa: E501
) -> dict:
    """Run an opencode agent with a prompt. Launches as background job; returns job_id for polling. Set wait=true to block until done."""  # noqa: E501

    if format not in ("text", "json"):
        return {"success": False, "message": f"Invalid format '{format}': must be 'text' or 'json'", "data": {}}  # noqa: E501

    # opencode >=1.18 CLI: --format accepts only 'default'|'json' (the old
    # 'text' choice errors out), and the working directory flag is --dir
    # (--project is not a run flag). Map the tool surface to the CLI.
    fmt = "json" if format == "json" else "default"
    cmd = [OPENCODE_BINARY, "run", prompt, "--format", fmt]
    if project:
        cmd.extend(["--dir", project])

    job_id = await create_job(prompt, project, timeout=timeout)

    if not wait:
        spawn_agent_background(job_id, cmd, timeout=timeout)
        return {
            "success": True,
            "message": "Agent started in background",
            "data": {
                "job_id": job_id,
                "prompt": prompt,
                "status": "queued",
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


async def opencode_launch_ui(
    project: Annotated[str | None, Field(description="Project directory to open. Uses cwd if omitted.")] = None,  # noqa: E501
    mode: Annotated[
        Literal["tui", "web", "serve"],
        Field(description="Launch mode: 'tui' (terminal UI), 'web' (browser), 'serve' (background API server)"),
    ] = "tui",  # noqa: E501
) -> dict:
    """Launch opencode interactively — TUI, web UI, or background API server. Use this to open the opencode interface for manual work."""  # noqa: E501

    binary = OPENCODE_BINARY

    if mode == "serve":
        cmd = [binary, "serve", "--port", "4096"]
    elif mode == "web":
        cmd = [binary, "web"]
        if project:
            cmd.append(project)
    else:
        cmd = [binary]
        if project:
            cmd.append(project)

    try:
        subprocess.Popen(
            cmd,
            cwd=project if project else os.getcwd(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == "nt" else 0,
        )
        return {
            "success": True,
            "message": f"opencode launched in {mode} mode for {project or os.getcwd()}",
            "data": {"mode": mode, "project": project, "binary": binary},
        }
    except FileNotFoundError:
        return {"success": False, "message": f"opencode binary not found: {binary}", "data": {}}  # noqa: E501
    except Exception as e:
        return {"success": False, "message": f"Failed to launch: {e}", "data": {}}
