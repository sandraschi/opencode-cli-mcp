import pytest

from opencode_cli_mcp.client import OPENCODE_BINARY
from opencode_cli_mcp.tools.agent import _build_run_cmd, opencode_run_agent


def test_build_default_cmd():
    cmd = _build_run_cmd("hello", "default")
    assert cmd[:4] == [OPENCODE_BINARY, "run", "hello", "--format"]
    assert cmd[4] == "default"
    assert "--auto" not in cmd and "--model" not in cmd


def test_build_full_options():
    cmd = _build_run_cmd(
        "fix it",
        "json",
        project=r"D:\Dev\repos\x",
        model="deepseek/deepseek-flash",
        agent="build",
        variant="high",
        thinking=True,
        auto=True,
        session_id="ses_1",
        fork=True,
        files=["a.log", "b.png"],
    )
    assert cmd[:5] == [OPENCODE_BINARY, "run", "fix it", "--format", "json"]
    assert cmd[cmd.index("--dir") + 1] == r"D:\Dev\repos\x"
    assert cmd[cmd.index("--model") + 1] == "deepseek/deepseek-flash"
    assert cmd[cmd.index("--agent") + 1] == "build"
    assert cmd[cmd.index("--variant") + 1] == "high"
    assert "--thinking" in cmd and "--auto" in cmd
    assert cmd[cmd.index("--session") + 1] == "ses_1"
    assert "--continue" not in cmd  # session wins
    assert "--fork" in cmd
    assert [cmd[i + 1] for i, t in enumerate(cmd) if t == "--file"] == ["a.log", "b.png"]


def test_build_continue_when_no_session():
    cmd = _build_run_cmd("go", "default", continue_session=True)
    assert "--continue" in cmd
    assert "--session" not in cmd


@pytest.mark.asyncio()
async def test_fork_requires_session():
    result = await opencode_run_agent(prompt="x", fork=True)
    assert result["success"] is False
    assert "fork requires" in result["message"]


@pytest.mark.asyncio()
async def test_missing_attachment_rejected(tmp_path):
    result = await opencode_run_agent(prompt="x", files=[str(tmp_path / "nope.log")])
    assert result["success"] is False
    assert "not found" in result["message"]
    assert result["data"]["missing"]
