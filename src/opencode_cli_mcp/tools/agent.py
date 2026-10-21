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


def _build_run_cmd(
    prompt: str,
    fmt: str,
    *,
    project: str | None = None,
    model: str | None = None,
    agent: str | None = None,
    variant: str | None = None,
    thinking: bool = False,
    auto: bool = False,
    session_id: str | None = None,
    continue_session: bool = False,
    fork: bool = False,
    files: list[str] | None = None,
) -> list[str]:
    """Translate tool options into an `opencode run` command line.

    Pure function so the flag mapping is testable without spawning anything.
    Flag choices follow `opencode run --help` (0.2.x):
    ``--model``, ``--agent``, ``--variant``, ``--thinking``, ``--auto``,
    ``--session``/``--continue``, ``--fork``, ``--file``, ``--dir``.
    """
    cmd = [OPENCODE_BINARY, "run", prompt, "--format", fmt]
    if project:
        cmd.extend(["--dir", project])
    if model:
        cmd.extend(["--model", model])
    if agent:
        cmd.extend(["--agent", agent])
    if variant:
        cmd.extend(["--variant", variant])
    if thinking:
        cmd.append("--thinking")
    if auto:
        cmd.append("--auto")
    if session_id:
        cmd.extend(["--session", session_id])
    elif continue_session:
        cmd.append("--continue")
    if fork:
        cmd.append("--fork")
    for path in files or []:
        cmd.extend(["--file", path])
    return cmd


async def opencode_run_agent(
    prompt: Annotated[str, Field(description="The prompt/message to send to the opencode agent")],
    project: Annotated[str | None, Field(description="Project directory path (optional)")] = None,
    format: Annotated[Literal["text", "json"], Field(description="Output format: 'text' or 'json'")] = "text",  # noqa: E501
    wait: Annotated[
        bool, Field(description="Wait for completion (true) or return immediately with job_id (false)")
    ] = False,  # noqa: E501
    timeout: Annotated[int, Field(description="Max seconds to wait when wait=true (default 300)")] = 300,  # noqa: E501
    model: Annotated[
        str | None,
        Field(description="Model as provider/model (e.g. 'deepseek/deepseek-flash'). Omit for opencode's default"),
    ] = None,
    agent: Annotated[
        str | None,
        Field(description="Agent to use (opencode agent name, e.g. 'build' or 'plan'). Omit for the default agent"),
    ] = None,
    variant: Annotated[
        str | None,
        Field(description="Provider-specific reasoning variant, e.g. 'high', 'max', 'minimal'"),
    ] = None,
    thinking: Annotated[bool, Field(description="Include thinking blocks in the output")] = False,
    auto: Annotated[
        bool,
        Field(
            description=(
                "Auto-approve permissions that are not explicitly denied (opencode --auto). "
                "Required for unattended runs that would otherwise block on an approval prompt."
            )
        ),
    ] = False,
    session_id: Annotated[
        str | None,
        Field(description="Continue this session instead of starting a new one (opencode --session)"),
    ] = None,
    continue_session: Annotated[
        bool,
        Field(description="Continue the most recent session (opencode --continue); ignored when session_id is set"),
    ] = False,
    fork: Annotated[
        bool,
        Field(description="Fork the session before continuing (requires session_id or continue_session)"),
    ] = False,
    files: Annotated[
        list[str] | None,
        Field(description="File paths to attach to the message (opencode --file). Must exist on disk."),
    ] = None,
) -> dict:
    """Run an opencode agent with a prompt, model, agent, and permission mode.

    Launches as background job; returns job_id for polling. Set wait=true to
    block until done. Unattended runs usually need ``auto=true`` - otherwise a
    permission prompt stalls the run until the timeout.

    ## Return Format
    {"success": bool, "message": str, "data": {"job_id": str, "status": str, "options": dict}}

    ## Examples
    opencode_run_agent(prompt="Refactor main.py", wait=False)
    opencode_run_agent(prompt="Summarize README", format="json", wait=True, timeout=120)
    opencode_run_agent(prompt="Fix tests", model="deepseek/deepseek-flash", agent="build", auto=True)
    opencode_run_agent(prompt="Continue the migration", session_id="ses_123", fork=True)
    """

    if format not in ("text", "json"):
        return {"success": False, "message": f"Invalid format '{format}': must be 'text' or 'json'", "data": {}}  # noqa: E501

    if fork and not (session_id or continue_session):
        return {
            "success": False,
            "message": "fork requires session_id or continue_session=true",
            "data": {},
        }

    missing = [p for p in (files or []) if not os.path.isfile(p)]
    if missing:
        return {
            "success": False,
            "message": f"Attachment(s) not found: {', '.join(missing)}",
            "data": {"missing": missing},
        }

    # opencode >=1.18 CLI: --format accepts only 'default'|'json' (the old
    # 'text' choice errors out), and the working directory flag is --dir
    # (--project is not a run flag). Map the tool surface to the CLI.
    fmt = "json" if format == "json" else "default"
    options = {
        "model": model,
        "agent": agent,
        "variant": variant,
        "thinking": thinking,
        "auto": auto,
        "session_id": session_id,
        "continue": continue_session,
        "fork": fork,
        "files": list(files or []),
    }
    cmd = _build_run_cmd(
        prompt,
        fmt,
        project=project,
        model=model,
        agent=agent,
        variant=variant,
        thinking=thinking,
        auto=auto,
        session_id=session_id,
        continue_session=continue_session,
        fork=fork,
        files=files,
    )

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
                "options": options,
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
            "options": options,
        },
    }


async def opencode_launch_ui(
    project: Annotated[str | None, Field(description="Project directory to open. Uses cwd if omitted.")] = None,  # noqa: E501
    mode: Annotated[
        Literal["tui", "web", "serve"],
        Field(description="Launch mode: 'tui' (terminal UI), 'web' (browser), 'serve' (background API server)"),
    ] = "tui",  # noqa: E501
) -> dict:
    """Launch opencode interactively - TUI, web UI, or background API server.

    Use this to open the opencode interface for manual work.

    ## Return Format
    {"success": bool, "message": str, "data": {"mode": str, "project": str}}

    ## Examples
    opencode_launch_ui(mode="web")
    opencode_launch_ui(mode="serve")
    """

    binary = OPENCODE_BINARY

    if mode == "serve":
        # Dedicated backend-owned port (NOT 4096 - the desktop app's
        # password-locked serve lives there). Matches OPENCODE_SERVE_URL.
        cmd = [binary, "serve", "--port", "4097"]
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
