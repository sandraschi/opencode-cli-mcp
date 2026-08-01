# opencode-cli-mcp — PRD

**Version**: 0.2.3 · **Status**: Active

## Purpose

Bridge [opencode](https://opencode.ai) (open-source AI coding agent) into the MCP ecosystem so LLM orchestrators (Claude, Cursor) can delegate implementation work to opencode running cheaper models. Tiered model economics: expensive high-judgment model plans, cheap model executes.

## Architecture

```
MCP Clients ──stdio──► opencode-cli-mcp ──httpx──► opencode serve (:4096)
Webapp SPA ──/api──► Unified backend :10951 (REST /api/* + FastMCP /mcp)
```

- **MCP surface**: 6 portmanteaus (runs, sessions, depot, system, mcpb_install, shutdown) + 15 legacy aliases
- **REST bridge**: FastAPI on the same ASGI app as the FastMCP Streamable HTTP endpoint
- **Session depot**: direct SQLite access to opencode's DB for archive/search/delete (offline-capable)
- **Frontend**: Vite/React fleet-standard dashboard (13 pages), experimental light-mode toggle

## Shipped Features (v0.2.x)

- Agent runs: start (fire-and-forget or blocking), status, list, cancel
- Session CRUD + transcript + diff via serve API
- **Session depot**: archive/unarchive/rename/delete/global transcript search/stats (SQLite)
- `.mcpb` bundle install into opencode config
- Graceful shutdown (MCP tool + REST)
- Unified backend: one port serves REST + MCP
- Webapp: dashboard KPIs, sessions, projects, tools hub, OC tools, apps hub, MCPB install, chat, help, settings, status, API docs, logs
- Ring-buffer request log (Logs page)
- Local LLM detection (Ollama/LM Studio/vLLM) in Settings

## Non-Goals (v0.2.x)

- No multi-client auth (single-user trust model)
- No scheduling beyond job store (no persistence across server restarts for runs)
- No write access to opencode sessions through the MCP surface beyond send/diff (depot covers metadata ops)

## Roadmap

- 0.3.0: remove legacy atomic aliases; portmanteau-only surface
- Tauri NSIS build hardening (CUA smoke green)
- Fleet-wide `just ci` verification in CI
