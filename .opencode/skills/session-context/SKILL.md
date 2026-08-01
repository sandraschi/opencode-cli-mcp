---
name: session-context
description: Lightweight opencode-cli-mcp session start prompt (tool awareness)
---

## Session Context (opencode-cli-mcp)

You have access to opencode-cli-mcp: it orchestrates opencode agent runs, sessions, and system diagnostics through opencode serve.

**Before starting work:**
1. Check server status: opencode_system(action="status")
2. Check recent runs: opencode_runs(action="list", limit=10)

**At end of work:**
- Review what changed: opencode_sessions(action="diff", session_id=...)
- Cancel stuck runs: opencode_runs(action="cancel", job_id=...)
