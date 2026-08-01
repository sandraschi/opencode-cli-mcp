# Onboarding — opencode-cli-mcp

The server delegates implementation work to **opencode**, so the
onboarding goal is: opencode serve running, MCP client connected,
first agent run green.

## 1. Prerequisites

| Requirement | Check |
|---|---|
| Python 3.12+ | `python --version` |
| opencode CLI | `opencode --version` (install: `npm i -g opencode-ai`) |
| MCP client | Claude Desktop / Cursor / Windsurf, or the desktop app |

## 2. Quick start (5 minutes)

```powershell
git clone https://github.com/sandraschi/opencode-cli-mcp
cd opencode-cli-mcp
just bootstrap
just start
```

`just start` brings up three processes:

| Process | Port | Purpose |
|---|---|---|
| opencode serve | 4096 | opencode HTTP API (autostarted) |
| FastAPI backend | 10951 | REST bridge + MCP HTTP |
| Vite frontend | 10950 | dashboard (opens in browser) |

## 3. First-run verification

1. Dashboard shows **opencode Server: Online** (top KPI).
2. Topbar dot is green (backend connected).
3. Run a first agent:
   - `opencode_system(action="status")` → `startup_probe.opencode_serve: true`
   - `opencode_runs(action="start", prompt="Hello, create hello.txt", wait=true)`
   - `opencode_sessions(action="diff", session_id=...)` → see `hello.txt`

## 4. Desktop app (no dev tools)

Download the NSIS installer. First launch copies `.env.example` to
`%LOCALAPPDATA%\com.sandraschi.opencode-cli-mcp\.env` and opens the
dashboard. opencode serve must be started separately (the operator
shell does not bundle the opencode CLI).

## 5. LLM chat

The Chat page auto-detects Ollama (:11434) or LM Studio (:1234).
Start one to enable chat; otherwise set a cloud provider (OpenAI,
Anthropic, Gemini, OpenRouter) in Settings.

## 6. Troubleshooting

- Backend red dot → topbar restart button, or `just api`.
- `opencode serve not reachable` in status → start
  `opencode serve` in a terminal.
- See docs/integration-guide.md and docs/USAGE.md for depth.
