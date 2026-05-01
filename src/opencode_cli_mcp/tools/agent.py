import subprocess
from typing import Annotated

from pydantic import Field

from opencode_cli_mcp.client import OPENCODE_BINARY


async def opencode_run_agent(
    prompt: Annotated[str, Field(description="The prompt/message to send to the opencode agent")],
    project: Annotated[str | None, Field(description="Project directory path (optional)")] = None,
    format: Annotated[str, Field(description="Output format: 'text' or 'json'")] = "text",
) -> dict:
    """Run an opencode agent non-interactively with a prompt. Uses `opencode run` under the hood. Best for delegating coding tasks to the opencode agent from within a larger workflow."""  # noqa: E501

    cmd = [OPENCODE_BINARY, "run", prompt, "--format", format]
    if project:
        cmd.extend(["--project", project])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        success = result.returncode == 0
        return {
            "success": success,
            "message": f"Agent failed (exit {result.returncode})"
            if not success
            else "Agent completed successfully",  # noqa: E501
            "data": {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
            },
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Agent run timed out after 300 seconds",
            "data": {},
        }
    except FileNotFoundError:
        return {
            "success": False,
            "message": f"opencode binary not found at '{OPENCODE_BINARY}'. Install with: npm i -g opencode-ai",  # noqa: E501
            "data": {},
        }
