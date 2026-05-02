# opencode-cli-mcp — Improvement Session Plan
**Date:** 2026-05-02  
**Context:** Post-async-fix session. DeepSeek V4 (Flash + Pro) as primary models.  
**Goal:** Make this a reliable fleet-sweep orchestration tool.

---

## Already Done Today

- [x] `opencode_run_agent` rewritten to use `asyncio.create_subprocess_exec` — event loop no longer blocked under parallel dispatch

---

## Priority Queue

### P1 — Do First (unblocks fleet sweep use case)

**1. `model` parameter on `opencode_run_agent`**

The single most valuable addition. Enables tiered economics per task:

```python
async def opencode_run_agent(
    prompt: str,
    project: str | None = None,
    model: str | None = None,   # e.g. "deepseek/deepseek-v4-flash", "deepseek/deepseek-v4-pro"
    format: str = "text",
    timeout: int = 300,
) -> dict:
```

Pass through as `opencode run --model <model>` if provided, otherwise let opencode use its configured default. Caller decides: lint sweep → Flash, architectural refactor → Pro or Sonnet.

Check opencode CLI: `opencode run --help` to confirm the flag name (may be `--model`, `--provider`, or a composite string).

**2. `timeout` parameter on `opencode_run_agent`**

Hardcoded 300s is wrong for both extremes. A docstring audit task on a small file should abort at 60s. A "refactor this entire server" task may need 600s. Trivial to add, big QoL improvement for fleet sweeps where you want fast failure on hung agents.

**3. Wire up `ensure_server()` or remove it**

Currently dead code. Every tool call will throw a raw httpx exception if `opencode serve` isn't running, with no helpful message. Two options:

- **Option A (recommended):** Call `await client.ensure_server()` at the top of each tool, return a clean `{"success": False, "message": "opencode serve not running — start with: opencode serve"}` if it fails. The auto-start behaviour in `_start_server()` is actually useful for cold-start resilience.
- **Option B:** Remove `ensure_server()` entirely, document the external dependency clearly, let the exception propagate with a better error message wrapper.

Option A is better for the fleet use case where you want zero-friction.

---

### P2 — High Value, Same Session

**4. `opencode_run_agent_async` — fire and return session ID**

The current tool waits for completion. For the 6-agent parallel sweep pattern, you want:

```
run_async → returns session_id immediately
list_sessions → poll for completion
get_messages → read output when done
```

opencode's HTTP API has the session layer already. The question is whether `opencode run` creates a trackable session or whether you need to use the `/session` + `/message` API directly to get async behaviour. Worth testing: does `opencode run` create a session visible in `opencode_list_sessions`?

If yes, `opencode_run_agent_async` just fires the subprocess without `await proc.communicate()` and returns whatever session ID opencode assigns.

**5. Fix `fleet.py` hardcoded port labels**

Load from `D:\Dev\repos\mcp-central-docs\operations\WEBAPP_PORTS.md` at startup. Parse the markdown table into a `{port: label}` dict. Already identified in ASSESSMENT.md — just needs doing. The fleet webapp dashboard is useless with 77 "unknown" labels.

**6. Replace `wmic` GPU query**

`wmic path win32_VideoController` is deprecated/absent on Windows 11. Replace with:

```python
import subprocess
result = subprocess.run(
    ["powershell", "-Command", "Get-CimInstance Win32_VideoController -Property Name | Select-Object -ExpandProperty Name"],
    capture_output=True, text=True
)
```

Or use `pywin32` WMI which is already in the venv.

---

### P3 — Nice to Have

**7. Module-level `OpencodeClient` singleton**

Each tool currently creates + destroys an `httpx.AsyncClient`. Fine for now, slightly wasteful. A lifespan-managed singleton (FastMCP supports lifespan context) would be cleaner and reuse the connection pool. Not urgent until you're doing high-frequency polling.

**8. `/api/tools` auto-derived from server**

`api/routes/tools.py` hardcodes the tool list and will silently drift. Either import the list from `server.py` directly or introspect the FastMCP app object. Low risk currently (9 tools, stable), worth fixing before the tool count grows.

**9. pytest asyncio mode**

Add to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```
pytest-asyncio 1.3.0 requires this. Current async tests may be running in sync mode and passing vacuously.

---

## Fleet Sweep Pattern (the end goal)

Once P1 items are done, the intended workflow:

```
Claude Desktop
  → opencode_run_agent(prompt="bug bash: fix all ruff violations", project="D:\\Dev\\repos\\aiwatcher-mcp", model="deepseek/deepseek-v4-flash", timeout=120)
  → opencode_run_agent(prompt="bug bash: fix all ruff violations", project="D:\\Dev\\repos\\arxiv-mcp", model="deepseek/deepseek-v4-flash", timeout=120)
  → ... × N repos, all concurrent
  → opencode_list_sessions() — poll until all done
  → opencode_get_messages(session_id) × N — collect results
  → summarise what was fixed / what failed
```

DeepSeek V4-Flash prompt cache means the static prefix ("bug bash: fix all ruff violations" + any system context) is paid once, then cache-hits for every subsequent repo call. Per-repo cost collapses to just the unique file content + output tokens.

---

## Open Questions

- Does `opencode run` accept `--model` flag? Check: `opencode run --help`
- Does `opencode run` create a visible session in `/session` API? If yes, async dispatch is easy.
- DeepSeek V4-Flash rate limiting behaviour under 6+ parallel agents — empirically seems fine, mechanism unknown. Worth logging response times per agent to characterise it.
- opencode winapp fires 6 agents visually — does it use `opencode serve` + HTTP API or direct subprocess per pane?
