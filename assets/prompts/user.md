# opencode-cli-mcp — User Guide

This tutorial walks you through the opencode-cli-mcp server from a
user's perspective: connecting it to your MCP client, launching your
first agent run, steering it mid-task, reviewing the work, and
integrating it into your daily fleet workflows. Each section assumes
you have opencode installed (`npm i -g opencode-ai` or the native
build) and, for the web features, the bundled dashboard.

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
and TypeScript (biome) before every commit.

### 1.3 Desktop app

Download the NSIS installer from the release page. One installer, one
shortcut: the desktop shell launches the embedded backend
automatically (port 10951) and opens the dashboard. No Python, Node,
uv, or git is required on the target machine. The backend loads
configuration from `.env.example` copied to the app data directory on
first launch.

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

and point your client at `http://127.0.0.1:10951/mcp` if you configure
the MCP streamable HTTP endpoint, or at the REST bridge for the
webapp. The `MCP_TRANSPORT=http` environment variable switches the
standalone server entry point to HTTP mode.

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
the timeout.

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

Returns the files created, modified, and deleted by the agent. This is
your primary review surface — always diff before accepting work.

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

### 4.6 Export a session

For the record, or to hand the work to a reviewer:

```
opencode_sessions(action="export", session_id="sess_01", format="markdown")
```

HTML export renders nicely in browsers and email.

## 5. Environment and fleet operations

### 5.1 Providers and project

```
opencode_system(action="providers")
opencode_system(action="project")
```

`providers` lists the LLM providers configured in opencode (models,
endpoints). `project` shows the current project context the agent
will work in.

### 5.2 Open the UI

Prefer the web interface for interactive work:

```
opencode_system(action="launch_ui", mode="web")
```

`mode` accepts `tui`, `web`, and `serve`.

### 5.3 MCP pulse

opencode aggregates other MCP servers through its config. Check that
they are all alive:

```
opencode_system(action="mcp_pulse")
```

Each configured server is probed; the response lists reachable and
dead servers. Dead servers surface as red entries — fix their config
or start them.

### 5.4 Config drift

Stale MCP configuration points at paths that no longer exist (for
example after a repo move):

```
opencode_system(action="config_drift")
```

This compares every configured server's path against the filesystem
and reports mismatches. Run it after restructuring your workspace.

## 6. Installing MCP bundles (.mcpb)

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

## 7. The web dashboard

Run `just start` (or the desktop app) and open
`http://localhost:10950`.

### 7.1 Dashboard

KPIs for opencode serve status, session count, MCP tool count, fleet
apps alive, CPU, and memory. The capabilities section shows the
feature flags; the tool surface section lists the atomic tools.

### 7.2 Sessions, Projects, Tools

- **Sessions** — browse opencode sessions, view transcripts and diffs.
- **Projects** — run history from the SQLite job store with status
  badges, stdout/stderr, and exit codes.
- **Tools** — the MCP tool registry, portmanteaus and legacy aliases,
  with descriptions.
- **OC Tools** — the six custom opencode tools this repo ships in
  `.opencode/tools/`, with install instructions and full source.
- **Apps Hub** — dynamic fleet discovery: live MCP webapps on this
  machine, registered vs experimental/untrusted.
- **MCPB Install** — graphical interface to `opencode_mcpb_install`
  with dry-run preview.
- **Status** — system info (CPU/memory/platform/GPU) and a live log
  stream.
- **API Docs** — Swagger UI and ReDoc for the FastAPI bridge.
- **Logs** — ring-buffer request log with filtering, search, export
  (JSON/CSV), tail mode, and clear.

### 7.2 Chat

The chat page uses your local LLM (Ollama on 11434 or LM Studio on
1234, auto-detected; cloud providers via Settings). Four personas
(Reductionist, Debugger, Explainer, Custom) shape the tone. The
prompt-refine button rewrites your input for clarity before sending.
Conversations persist in localStorage (capped at 100 messages) and
export to a timestamped text file.

### 7.3 Settings

- Appearance: dark/light theme.
- opencode serve URL (default `http://127.0.0.1:4096`).
- Local LLM: provider, endpoint, model — auto-detected models listed
  when Ollama/LM Studio are running.
- Cloud provider: OpenAI, Anthropic, Google Gemini, OpenRouter with
  API key and model.

Settings persist server-side via `/api/settings`.

## 8. Custom opencode tools

The repo ships six TypeScript custom tools in `.opencode/tools/` that
give opencode's own LLM direct access to the fleet management API:
`fleet`, `sessions`, `runs`, `system`, `providers`, and `tools`. Copy
them into any opencode project:

```powershell
cp -r .opencode/tools/* <your-project>/.opencode/tools/
```

Restart opencode; the LLM can now call these tools to scan the fleet,
inspect sessions, and diagnose servers without leaving the chat.

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `startup_probe.opencode_serve: false` | opencode serve not running | Start `opencode serve` (or allow autostart on first call) |
| Run stuck in `queued` | Job store locked by another process | Wait for the other client, or restart the backend |
| `Prefab cards not registered` on stderr | prefab-ui not synced or disabled | `uv sync`, or unset `OPENCODE_CLI_MCP_PREFAB_APPS=0` |
| Webapp shows "Failed to fetch" | Backend not running on 10951 | `just api` or restart via the topbar restart button |
| Chat shows "No LLM detected" | Ollama/LM Studio not running | Start one; the indicator refreshes automatically |
| `just type-check` fails | pyright not installed | `uv sync --group dev` then `uv run pyright` |
| Installer opens but dashboard offline | Backend child crashed | Check `%LOCALAPPDATA%\opencode-cli-mcp\logs\backend-spawn.log` |

## 10. Security notes

opencode-cli-mcp runs arbitrary shell commands through agent runs
driven by LLM prompts. Only use it where you trust your MCP client and
models. The REST API binds to loopback; the CORS configuration covers
localhost, Tauri origins, Tailscale, and LAN IPs. Keep your API keys in
`.env` (never committed; `.env.example` is the committed template).
