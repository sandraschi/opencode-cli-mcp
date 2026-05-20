# opencode-cli-mcp — Improvement Plan

**Date:** 2026-05-05  
**Status:** Active development

---

## Fixed in 2026-05-05 Sessions

- [x] Wire up `ensure_server()` in all MCP session/status tools — clean error if opencode not running
- [x] Auto-derive `/api/tools` from shared `registry.py` — no more hardcoded drift
- [x] Fix `fleet.py` missing labels — all ports from WEBAPP_PORTS.md now labeled
- [x] Fix 24+ ruff lint errors (imports, bare except, line length, unused vars)
- [x] Comprehensive docs: USAGE.md, improved README, improved integration guide
- [x] Shorten tool descriptions in registry to fit within line-length rules
- [x] Fix Settings page — removed mock labels, theme toggle now applies to document root, proper LLM config
- [x] Fix Help page — auto-discovers all docs from backend, renders markdown, adds search filter
- [x] Add docs backend endpoint (`GET /api/docs`, `GET /api/docs/{id}`)
- [x] Create 6 OpenCode custom tools (`.opencode/tools/`) — fleet, sessions, runs, system, providers, tools
- [x] Add backend endpoint for custom tool definitions (`GET /api/opencode-tools`)
- [x] Add webapp page `/oc-tools` — install guide, tool previews, copy-to-clipboard
- [x] Add CHANGELOG.md
- [x] `llms.txt` and `llms-full.txt` for MCPB packing

## Previously Fixed

- [x] `opencode_run_agent` rewritten to `asyncio.create_subprocess_exec` — no event loop blocking
- [x] GPU detection uses `Get-CimInstance` (not deprecated `wmic`)
- [x] `asyncio_mode = "auto"` set in pyproject.toml
- [x] `timeout` parameter exposed on `opencode_run_agent`

---

## P1 — High Priority

**1. `model` parameter on `opencode_run_agent`**

Enables tiered economics: use DeepSeek Flash for lint sweeps, Pro for refactoring.

```python
opencode_run_agent(
    prompt="fix all ruff violations",
    model="deepseek/deepseek-v4-flash",  # pass --model to opencode run
)
```

Needs: verify `opencode run --model` flag exists, then pass through in `agent.py`.

**2. `opencode_run_agent_async` — fire and return session ID**

For the 6-agent parallel sweep pattern, you want:

```
run_async -> returns session_id immediately
list_sessions -> poll for completion  
get_messages -> read output when done
```

Needs: test whether `opencode run` creates a visible session in `/session` API.

**3. Add `show_dashboard_card` tool**

FastMCP 3.2 Prefab UI — render server status as a rich card in chat. Pattern: other fleet MCPs already have this.

---

## P2 — High Value

**4. Module-level `OpencodeClient` singleton**

Each tool creates + destroys an `httpx.AsyncClient`. Fine for now, but a lifespan-managed singleton would reuse the connection pool. Not urgent until high-frequency polling.

**5. Load fleet labels from `mcp-central-docs` at startup**

The fleet.py label dict still hardcodes ~90 port entries. Ideal: parse `WEBAPP_PORTS.md` or `webapp-registry.json` at startup so it never drifts.

**6. Fix Chat page Ollama direct call**

`Chat.tsx` calls `http://127.0.0.1:11434/api/generate` directly from browser. Works only if browser can reach Ollama. Should route through backend proxy.

---

## P3 — Nice to Have

**7. Add tests for tool logic and client**

Current tests only verify tool registration. Add:
- `OpcencodeClient` unit tests with mocked HTTP
- `job_store` operation tests  
- API route integration tests

**8. SSE passthrough for live session output**

`opencode_get_messages` currently polls. For real-time session monitoring, consider SSE passthrough.

**9. Add `llms.txt`**

The `.mcpbignore` references `llms.txt` / `llms-full.txt` for MCPB packing. Create these for better LLM discovery.

---

## Fleet Sweep Pattern (strategic goal)

Once P1 items are done, the intended workflow:

```
Claude Desktop
  -> opencode_run_agent(prompt="bug bash: fix all ruff violations",
       project="D:\\Dev\\repos\\aiwatcher-mcp",
       model="deepseek/deepseek-v4-flash", timeout=120)
  -> opencode_run_agent(prompt="bug bash: fix all ruff violations",
       project="D:\\Dev\\repos\\arxiv-mcp",
       model="deepseek/deepseek-v4-flash", timeout=120)
  -> ... x N repos, all concurrent
  -> opencode_list_sessions() — poll until all done
  -> opencode_get_messages(session_id) x N — collect results
  -> summarise what was fixed / what failed
```

The bottleneck shifts from token cost to review bandwidth.
