# opencode-cli-mcp — User Guide

This tutorial walks you through the opencode-cli-mcp server from a
user's perspective: connecting it to your MCP client, launching your
first agent run, steering it mid-task, reviewing the work, archiving
and searching sessions in the depot, and integrating it into your
daily fleet workflows. Each section assumes you have opencode
installed (`npm i -g opencode-ai` or the native build) and, for the
web features, the bundled dashboard.

## 1. Installation and first start

### 1.1 Requirements

- Python 3.12 or newer.
- The `opencode` CLI (version 2.x or later).
- An MCP client: Claude Desktop, Cursor, Windsurf, or the bundled
  desktop app (NSIS installer, which ships everything including a
  Python backend frozen with PyInstaller — no Python needed on the
  target machine).

### 1.2 Developer install

Clone the repository and install dependencies with the just task
runner (or uv directly):

```powershell
git clone https://github.com/sandraschi/opencode-cli-mcp
cd opencode-cli-mcp
just bootstrap      # uv sync + pre-commit hooks
just start          # opencode serve (:4096) + FastAPI backend (:10951) + Vite frontend (:10950)
```

`just bootstrap` installs Python dev dependencies (pytest, ruff,
pre-commit) and registers the pre-commit hooks that lint Python (ruff)
and TypeScript (biome) before every commit. The certification command
`just certify` runs all five gates — ruff, pytest, pyright, tsc, and
biome — and aborts on the first failure.

### 1.3 Desktop app

Download the NSIS installer from the release page. One installer, one
shortcut: the desktop shell launches the embedded backend
automatically (port 10951) and opens the dashboard. No Python, Node,
uv, or git is required on the target machine. The backend loads
configuration from `.env.example` copied to the app data directory on
first launch.

### 1.4 What starts on `just start`

The start script clears stale port holders, then launches three
processes: `opencode serve` on port 4096 (the CLI's HTTP API), the
unified backend on port 10951 (REST `/api/*` plus the FastMCP
Streamable HTTP endpoint at `/mcp`), and the Vite frontend on port
10950. A readiness poll waits for the backend health endpoint before
opening the browser.

## 2. Connecting to an MCP client

### 2.1 Claude Desktop

Add a server entry to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "opencode-cli-mcp": {
      "command": "uv",
      "args": ["run", "python", "-m", "opencode_cli_mcp.server"]
    }
  }
}
```

opencode serve must already be running on port 4096
(`opencode serve` in a terminal), or the startup probe will report it
unreachable and the first tool call will attempt an autostart.

### 2.2 Cursor / Windsurf

Same configuration as above via the IDE's MCP settings panel. The
server exposes its tools over stdio; no extra flags are required.

### 2.3 HTTP transport

For remote or shared setups, run the backend explicitly:

```powershell
uv run python -m api.main          # FastAPI on 10951
```

and point your client at `http://127.0.0.1:10951/mcp` for the MCP
Streamable HTTP endpoint, or at the REST bridge for the webapp. This
is also how the Tauri desktop app connects while it is running. The
port can be overridden with `OPENCODE_CLI_MCP_PORT` (run_server.py)
or `BACKEND_PORT` (api.main).

### 2.4 Verify the connection

After configuration, ask your assistant to run
`opencode_system(action="status")`. A successful response confirms
the server is mounted and shows whether `opencode serve` is
reachable. If the tool list is empty, check the client's MCP logs —
the most common cause is a missing `uv` on PATH or a syntax error in
the JSON config.

## 3. Your first agent run

### 3.1 Check connectivity

Before launching anything, verify opencode serve is reachable:

```
opencode_system(action="status")
```

You should see `data.startup_probe.opencode_serve: true` (or a clear
"not reachable, will autostart" message). If the probe failed, start
`opencode serve` manually and retry.

### 3.2 Launch a short task (blocking)

For a quick, well-scoped task you can block:

```
opencode_runs(action="start", prompt="Add type hints to src/client.py", wait=true, timeout=120)
```

The call returns when the run finishes, with the agent's final output
and exit code. Use this only for tasks you expect to complete within
the timeout — blocking calls risk client timeouts (4-5 minutes on
most hosts).

### 3.3 Launch a long task (fire-and-forget)

For anything longer, do not block:

```
opencode_runs(action="start", prompt="Refactor the tools package into portmanteaus", wait=false)
```

The response includes a `job_id` such as `abc123`. Poll it:

```
opencode_runs(action="status", job_id="abc123")
```

The status response shows `queued`, `running`, or `completed` (plus
`failed`/`cancelled`), the accumulated output so far, and the exit
code once done. Poll every 5-10 seconds for long runs; the job store
persists across server restarts, so an interrupted session does not
lose the run.

### 3.4 Cancel a stuck run

If the agent goes off-course, stop it immediately:

```
opencode_runs(action="cancel", job_id="abc123")
```

The run is marked `cancelled`; the child process is terminated. You
can then review what it did before cancellation and resume with
corrections.

### 3.5 Launch several runs at once (multi-agent sweep)

Fire-and-forget makes parallel sweeps trivial:

```
opencode_runs(action="start", prompt="Bump the pinned version in justfile", project="D:/Dev/repos/repo-a", wait=false)
opencode_runs(action="start", prompt="Bump the pinned version in justfile", project="D:/Dev/repos/repo-b", wait=false)
opencode_runs(action="start", prompt="Bump the pinned version in justfile", project="D:/Dev/repos/repo-c", wait=false)
```

Collect the three job_ids, poll them in a loop, then diff each
resulting session. Keep each prompt scoped to one project so a
failure in one run does not cascade into the others.

## 4. Working with sessions

Every run creates an opencode session. Sessions are your window into
what the agent actually did.

### 4.1 List sessions

```
opencode_sessions(action="list", limit=20)
```

Each session entry carries an id and metadata. The list is paginated:
use `offset` and honor `next_offset` to walk long histories.

### 4.2 Read the transcript

```
opencode_sessions(action="messages", session_id="sess_01")
```

The transcript shows the agent's reasoning steps, tool calls, and
file edits in order. Use it to understand decisions before reviewing
the diff.

### 4.3 Review the diff

```
opencode_sessions(action="diff", session_id="sess_01")
```

Returns the files created, modified, and deleted by the agent. This
is your primary review surface — always diff before accepting work.
The diff response groups files by operation so you can skim the
change set at a glance.

### 4.4 Steer mid-task (interactive supervision)

This is the flagship workflow. While a run is executing:

1. Read its latest messages:
   `opencode_sessions(action="messages", session_id="sess_01")`
2. Send a correction:
   `opencode_sessions(action="send", session_id="sess_01", message="Do not touch the tests directory, only refactor src/")`
3. The agent acknowledges and adjusts its plan, then continues.

You can iterate this loop as often as needed. This turns a blind
delegation into supervised pair-programming with a cheaper model.

### 4.5 Search across sessions

Forgot which session touched a file? Grep the message history:

```
opencode_sessions(action="grep", query="portmanteau")
```

The grep spans all sessions and returns matching message excerpts
with session references, so you can jump straight to the relevant
context.

### 4.6 Export a session

For the record, or to hand the work to a reviewer:

```
opencode_sessions(action="export", session_id="sess_01", format="markdown")
```

HTML export renders nicely in browsers and email.

## 5. The session depot

The depot is opencode-cli-mcp's own archive layer over the opencode
SQLite database (`~/.local/share/opencode/opencode.db`). It works
without `opencode serve` and adds operations the serve API and the
opencode UI lack: archiving, unarchiving, renaming, permanent
deletion, full-text search, and statistics.

### 5.1 Browse the depot

```
opencode_depot(action="list", limit=50)
```

Unarchived sessions come first. Filter by `status` ("archived" /
"unarchived"), `project`, or a `timeframe` window. As with every
list tool, honor `next_offset` to page through everything.

### 5.2 Archive and unarchive

Keep the unarchived list short by archiving completed milestones:

```
opencode_depot(action="archive", session_id="sess_01")
```

Restore any time with the operation that exists nowhere else:

```
opencode_depot(action="unarchive", session_id="sess_01")
```

Archived sessions are fully searchable, so nothing is lost when you
archive — only hidden from the default list.

### 5.3 Rename

Give sessions meaningful titles before archiving:

```
opencode_depot(action="rename", session_id="sess_01", name="Fix portmanteau pagination")
```

Search then matches both titles and transcript content.

### 5.4 Search the archive

The fastest way to re-find a decision recorded months ago:

```
opencode_depot(action="search", query="why did we pin uvicorn to 0.34")
```

Search uses SQLite FTS5 with BM25 ranking — phrase it naturally, read
the ranked results, and open the winning session with
`opencode_sessions(action="get", ...)`.

### 5.5 Stats

```
opencode_depot(action="stats")
```

Reports total sessions, archived vs unarchived counts, storage
footprint, and a per-project breakdown. Run it after any depot
cleanup to confirm the new totals.

### 5.6 Delete (permanent, be careful)

```
opencode_depot(action="delete", session_id="sess_01", confirm=true)
```

Deletion cascades through the session's messages, files, and parts —
there is no recovery. It is safest when opencode is idle, and you
should always confirm the target with `list` or `search` first. The
depot is the intended way to remove sensitive or junk sessions that
the opencode UI cannot delete.

## 6. Environment and fleet operations

### 6.1 Providers and project

```
opencode_system(action="providers")
opencode_system(action="project")
```

`providers` lists the LLM providers configured in opencode (models,
endpoints). `project` shows the current project context the agent
will work in.

### 6.2 Open the UI

Prefer the web interface for interactive work:

```
opencode_system(action="launch_ui", mode="web")
```

`mode` accepts `tui`, `web`, and `serve`.

### 6.3 MCP pulse

opencode aggregates other MCP servers through its config. Check that
they are all alive:

```
opencode_system(action="mcp_pulse")
```

Each configured server is probed; the response lists reachable and
dead servers. Dead servers surface as red entries — fix their config
or start them.

### 6.4 Config drift

Stale MCP configuration points at paths that no longer exist (for
example after a repo move):

```
opencode_system(action="config_drift")
```

This compares every configured server's path against the filesystem
and reports mismatches. Run it after restructuring your workspace.

## 7. Installing MCP bundles (.mcpb)

opencode-cli-mcp can install other servers' `.mcpb` bundles into your
opencode configuration:

```
opencode_mcpb_install(source="./dist/arxiv-mcp-v1.0.0.mcpb", dry_run=true)
```

The dry run prints exactly what would be merged. Review it, then:

```
opencode_mcpb_install(source="./dist/arxiv-mcp-v1.0.0.mcpb", dry_run=false)
```

Use `name_override` when the bundle's server name collides with an
existing entry. Source may be a `.mcpb` file or an unpacked MCPB
directory. The merge is written to
`~/.config/opencode/opencode.json`; run `mcp_pulse` afterwards to
verify the new server is live.

## 8. The web dashboard

Run `just start` (or the desktop app) and open
`http://localhost:10950`.

### 8.1 Dashboard

KPIs for opencode serve status, session count, MCP tool count, fleet
apps alive, CPU, and memory. The capabilities section shows the
feature flags; the tool surface section lists the atomic tools. A
hero section links to onboarding and the installation guide.

### 8.2 Sessions, Projects, Tools

- **Sessions** — browse opencode sessions, view transcripts and diffs.
- **Projects** — run history from the SQLite job store with status
  badges, stdout/stderr, and exit codes.
- **Tools** — the MCP tool registry, portmanteaus and legacy aliases,
  with descriptions and input schemas.
- **OC Tools** — the six custom opencode tools this repo ships in
  `.opencode/tools/`, with install instructions and full source.
- **Apps Hub** — dynamic fleet discovery: live MCP webapps on this
  machine, registered vs experimental/untrusted.
- **MCPB Install** — graphical interface to `opencode_mcpb_install`
  with dry-run preview.
- **Status** — system info (CPU/memory/platform/GPU) and a live log
  stream with an auto-scroll toggle.
- **API Docs** — Swagger UI and ReDoc for the FastAPI bridge.
- **Logs** — ring-buffer request log with filtering, search, export
  (JSON/CSV), and clear.

### 8.3 Chat

The chat page uses your local LLM (Ollama on 11434 or LM Studio on
1234, auto-detected; cloud providers via Settings). Four personas
(Reductionist, Debugger, Explainer, Custom) shape the tone. The
prompt-refine button rewrites your input for clarity before sending.
Conversations persist in localStorage (capped at 100 messages) and
export to a timestamped text file. The provider/model selected in
Settings is shared with the chat header, so the badge reflects your
choice without reloading.

### 8.4 Settings

- opencode serve URL (default `http://127.0.0.1:4096`).
- Local LLM: provider, endpoint, model — auto-detected models listed
  when Ollama/LM Studio are running.
- Cloud provider: OpenAI, Anthropic, Google Gemini, OpenRouter with
  API key and model.

Settings persist server-side via `/api/settings`; provider and model
selections also persist in localStorage for the chat header.

## 9. Custom opencode tools

The repo ships six TypeScript custom tools in `.opencode/tools/` that
give opencode's own LLM direct access to the fleet management API:
`fleet`, `sessions`, `runs`, `system`, `providers`, and `tools`. Copy
them into any opencode project:

```powershell
cp -r .opencode/tools/* <your-project>/.opencode/tools/
```

Restart opencode; the LLM can now call these tools to scan the fleet,
inspect sessions, and diagnose servers without leaving the chat.

## 10. Best practices

### 10.1 Prompt discipline

- One focused task per run. A broad prompt produces a broad diff
  that is hard to review.
- Give the project path explicitly when the target is not the
  server's working directory.
- Include acceptance criteria in the prompt ("add tests", "do not
  touch lockfiles") — agents follow constraints better than
  intentions.

### 10.2 Review before accept

- Always `diff` the session before accepting work.
- Read the transcript when the diff touches files you did not expect.
- If the result is wrong, `send` a correction instead of re-running
  from scratch — the agent keeps its context.

### 10.3 Session hygiene

- Archive after every milestone; unarchiving is always possible.
- Rename sessions with meaningful titles before archiving.
- Search the depot before re-doing work — you may have already
  solved it.
- Delete only disposable sessions, and only with `confirm=true`.

### 10.4 Cost and speed

- DeepSeek V4 Flash (or the cheapest model your provider offers) is
  the usual delegate; keep the expensive model for planning and
  review.
- Prefer fire-and-forget + polling over blocking for anything longer
  than a minute.
- Batch independent work into parallel sweeps rather than a
  sequential chain.

## 11. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `startup_probe.opencode_serve: false` | opencode serve not running | Start `opencode serve` (or allow autostart on first call) |
| Run stuck in `queued` | Job store locked by another process | Wait for the other client, or restart the backend |
| `Prefab cards not registered` on stderr | prefab-ui not synced or disabled | `uv sync`, or unset `OPENCODE_CLI_MCP_PREFAB_APPS=0` |
| Webapp shows "Failed to fetch" | Backend not running on 10951 | `just api` or restart via the topbar restart button |
| Chat shows "No LLM detected" | Ollama/LM Studio not running | Start one; the indicator refreshes automatically |
| `just type-check` fails | pyright not installed | `uv sync --group dev` then `uv run pyright` |
| Installer opens but dashboard offline | Backend child crashed | Check `%LOCALAPPDATA%\opencode-cli-mcp\logs\backend-spawn.log` |
| Tool count below 21 after upgrade | Stale frozen binary | Rebuild the backend (`just build-native`) |
| Depot search returns nothing | Wrong database path | Verify `OPENCODE_DB_PATH` / `XDG_DATA_HOME` resolve to the real opencode.db |
| MCP tools missing in client | `uv` not on PATH | Install uv and restart the client |

## 12. FAQ

**Does the depot need opencode running?** No. Depot operations read
the SQLite database directly. Only runs, sessions, and system actions
talk to `opencode serve`.

**Can I run the stdio server and the desktop app at the same time?**
Yes, but they share the job store and the serve port. The desktop app
owns the HTTP backend; use the stdio server for IDE clients. Avoid
launching duplicate runs from both at once.

**What happens if my machine restarts mid-run?** The job store
persists. On restart, `opencode_runs(action="status", job_id=...)`
reports the run's last known state; the child process itself may not
survive, so treat interrupted runs as failed and re-run.

**Is it safe to run arbitrary prompts?** The server executes shell
commands inside agent runs driven by LLM prompts. Only use it where
you trust the client and models. Destructive MCP operations
(`depot delete`, `shutdown`) are confirmation-gated.

**Why is the tool list different from the README count?** The README
and diagnostics report 21 tools (6 portmanteaus + 15 legacy aliases).
Legacy aliases are deprecated and disappear in 0.3.0, so counts will
drop then — the portmanteaus cover everything the aliases did.

**How do I update?** `git pull` (or reinstall the NSIS package),
then `uv sync` and restart. Version is aligned across eight files;
the changelog documents what changed per release.

## 13. Worked example: supervised refactor

This end-to-end walkthrough ties the whole surface together. The
task: refactor a large Python package into portmanteau tools without
touching the test suite, with the user supervising.

**Step 1 — check the environment.**

```
opencode_system(action="status")
opencode_system(action="project")
```

Both return healthy; the project is the target repo.

**Step 2 — launch the run, fire-and-forget.**

```
opencode_runs(action="start",
  prompt="Refactor src/tools/ into portmanteau tools with operation enums. Do not modify tests/. Add [RATIONALE] sections to docstrings.",
  project="D:/Dev/repos/example-repo",
  wait=false)
```

Returns `job_id: "r_7f3a"`.

**Step 3 — read the transcript while it works.**

After a minute:

```
opencode_sessions(action="messages", session_id="sess_9c1e")
```

The agent is consolidating the six legacy tools into two portmanteaus
— on plan.

**Step 4 — steer when it drifts.**

```
opencode_sessions(action="send",
  session_id="sess_9c1e",
  message="Keep the operation enum names identical to the current function names so callers stay compatible.")
```

The agent confirms and adjusts.

**Step 5 — poll to completion.**

```
opencode_runs(action="status", job_id="r_7f3a")
```

Repeated every 10 seconds until `status: "completed"`, `exit_code: 0`.

**Step 6 — review the diff.**

```
opencode_sessions(action="diff", session_id="sess_9c1e")
```

Two new files, four renames, tests untouched — exactly as instructed.

**Step 7 — archive and record.**

```
opencode_depot(action="rename", session_id="sess_9c1e", name="Refactor tools into portmanteaus")
opencode_depot(action="archive", session_id="sess_9c1e")
opencode_depot(action="stats")
```

The session is archived with a searchable title; stats confirm the
archive grew by one.

## 14. Deployment scenarios

### 14.1 Developer machine (typical)

`just start` runs serve, backend, and frontend together. Use the
stdio server in your IDE client and the dashboard in the browser.
This is the setup this guide assumes.

### 14.2 Desktop app (non-developer)

The NSIS installer gives a non-developer (for example a project
partner) the full experience without Python or Node: dashboard,
local LLM chat, and MCP access while the app runs. Session depot and
runs work identically; the embedded backend owns the job store.

### 14.3 Remote / shared backend

Run `uv run python -m api.main` on a machine reachable over your
Tailscale network. Point clients at
`http://<tailscale-ip>:10951/mcp`. CORS already covers `*.ts.net`
and LAN addresses, so the dashboard works from another device on the
same network.

### 14.4 CI / automation

Headless runs are driven entirely through the MCP tools or the REST
bridge (`POST /api/runs`, `GET /api/runs/{id}`). The job store makes
runs resumable across pipeline retries. Use `wait=false` and poll —
pipeline timeouts are usually shorter than blocking agent runs.

## 15. Fleet integration

opencode-cli-mcp slots into the wider MCP fleet:

- **aiwatcher-mcp**: fleet events from completed runs can be
  ingested for the daily digest, keeping the team aware of agent
  activity across repos.
- **git-github-mcp**: use opencode runs for the mechanical work and
  git tools for the resulting review and commit flow.
- **calibre-mcp / arxiv-mcp**: archive research outputs produced by
  runs into the Calibre library via their respective tools.
- **Fleet pulse**: `opencode_system(action="mcp_pulse")` verifies all
  configured servers in one call — the standard health check before
  a fleet-wide operation.
- **Session depot as project memory**: search the depot before
  starting related work to recall prior decisions, file layouts, and
  constraint notes recorded in old sessions.

The custom opencode tools (`.opencode/tools/`) extend opencode's own
agent with the same fleet awareness, so opencode can check fleet
health itself without an MCP round-trip.

## 16. Agentic patterns

Beyond the basic workflows, these patterns get the most out of the
server in day-to-day use.

### 16.1 Verify-and-fix loop

When a run completes with `exit_code != 0` or a diff you reject:

1. Read the transcript tail: `opencode_sessions(action="messages")`.
2. Identify the failure point (usually a model error, a wrong
   assumption, or a missing constraint).
3. Send a corrective instruction:
   `opencode_sessions(action="send", session_id=..., message="The build fails because the import path is src/pkg, not pkg. Fix and rerun the checks.")`
4. Poll `opencode_runs(action="status")` — the corrected run reuses
   the session context instead of starting cold.

This converges faster than cancelling and re-launching, because the
agent keeps its accumulated understanding.

### 16.2 Investigate-before-act

Before delegating a change, use the depot as project memory:

1. `opencode_depot(action="search", query="<feature or module name>")`.
2. Read the winning session's diff to recall the file layout and
   past constraints.
3. Write a prompt that references those constraints explicitly.

Agents that start with prior context produce fewer rewrites.

### 16.3 Tiered delegation

The fleet's economics pattern: plan with the expensive model, execute
with the cheap one.

1. Use your main assistant to decompose the work and write precise
   prompts (that is this conversation).
2. Launch opencode runs on DeepSeek V4 Flash (or your provider's
   cheapest capable model).
3. Review diffs with the main assistant; loop via `send` for fixes.

### 16.4 Batch review

For a multi-agent sweep, review in bulk:

1. `opencode_runs(action="list", limit=20)` — see all recent runs and
   their statuses in one call.
2. For each completed run, `opencode_sessions(action="diff")` the
   matching session.
3. Archive the accepted ones, `send` corrections on the rejected
   ones, and `stats` at the end.

### 16.5 Chat-assisted planning

The dashboard chat page runs against your local LLM (Ollama, LM
Studio, or vLLM — auto-detected, cloud providers via Settings) and is
useful for planning work that will later run as opencode agents:

1. Draft the task in chat with the Explainer or Debugger persona to
   sharpen the wording.
2. Use the prompt-refine button to tighten the final instruction.
3. Hand the refined prompt to `opencode_runs(action="start", ...)` —
   precise prompts make cheaper models perform better.

The chat keeps a 100-message history in localStorage and exports to a
timestamped text file, so plans survive restarts and can be shared.

## 17. The REST bridge for automation

Power users and scripts can drive the same surface over HTTP on port
10951, without an MCP client:

```powershell
# Health + diagnostics (tool count, system stats)
Invoke-RestMethod http://127.0.0.1:10951/api/v1/health
Invoke-RestMethod http://127.0.0.1:10951/api/v1/diagnostics

# Launch a run and poll it
$body = @{ prompt = "Run the test suite and fix failures"; wait = $false } | ConvertTo-Json
$run  = Invoke-RestMethod -Method Post http://127.0.0.1:10951/api/runs -Body $body -ContentType "application/json"
$status = Invoke-RestMethod http://127.0.0.1:10951/api/runs/$($run.data.job_id)

# Read the ring-buffer logs
Invoke-RestMethod "http://127.0.0.1:10951/api/logs?level=ERROR"
```

The OpenAPI description lives at `http://127.0.0.1:10951/docs`
(Swagger UI) and `/redoc`; the dashboard's API Docs page embeds both.
Use the REST bridge for cron jobs, CI steps, and dashboards; keep the
MCP tools for interactive assistant work.

Common automation flows:

- **Nightly sweep**: launch one run per repo with the same mechanical
  prompt, poll all, write the diffs to a summary file.
- **Health monitor**: poll `/api/v1/health` and `/api/opencode/status`
  from a watchdog; alert when serve goes down.
- **Log review**: export `GET /api/logs/export?format=json` after a
  failure to keep a permanent audit trail.
- **Shutdown**: `POST /api/shutdown` stops the backend cleanly in
  scripts and installers.

## 18. Glossary

- **opencode** — the open-source AI coding agent CLI that this server
  wraps. Runs in the terminal, web, or serve mode.
- **opencode serve** — opencode's HTTP API mode, the transport this
  server talks to over httpx.
- **Run** — a single agent execution launched via
  `opencode_runs(action="start")`, tracked in the job store.
- **Session** — opencode's record of an agent conversation, including
  reasoning, tool calls, and file edits.
- **Job store** — SQLite database persisting run state across server
  restarts.
- **Session depot** — this server's archive/search layer over
  opencode's own SQLite database; works offline.
- **Portmanteau** — a consolidated MCP tool with an `operation`
  discriminator instead of many atomic tools.
- **Prefab card** — an in-chat rich UI rendered by MCP Apps in
  capable hosts (Claude Desktop, opencode).
- **Streamable HTTP** — the MCP transport served at `/mcp` on the
  unified backend.
- **FTS5** — SQLite's full-text search engine backing depot search.

## 19. Security notes

opencode-cli-mcp runs arbitrary shell commands through agent runs
driven by LLM prompts. Only use it where you trust your MCP client and
models. The REST API binds to loopback; the CORS configuration covers
localhost, Tauri origins, Tailscale, and LAN IPs. Keep your API keys in
`.env` (never committed; `.env.example` is the committed template).
The session depot can delete sessions permanently — treat `delete` as
you would any destructive database operation. Runs launched through
the server can modify files anywhere the opencode process can write;
scope prompts and project paths accordingly, and use `cancel` early
when an agent wanders outside its intended target.
