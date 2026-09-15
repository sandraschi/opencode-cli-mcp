# Tools — opencode-cli-mcp

Six primary portmanteaus (plus 15 legacy aliases slated for removal in 0.3.0).
Every tool returns `{success, message, data}`.

| Tool | Purpose | Key actions |
|------|---------|-------------|
| `opencode_runs` | Delegate work to opencode agents | `start` (prompt, wait flag → job_id), `status`, `list`, `cancel` |
| `opencode_sessions` | Live session CRUD over `opencode serve` | `list`, `get`, `messages`, `send`, `diff`, `rename`, `delete`, `export` |
| `opencode_depot` | Eternal memory over `opencode.db` (works offline) | `list`, `get`, `search` (FTS5), `rag` / `rag_index` / `rag_status`, `archive`, `unarchive`, `rename`, `delete`, `stats` |
| `opencode_backups` | Depot + config safety | `create`, `list`, `prune`, `restore` (guarded while serve runs), `status` |
| `opencode_system` | Server self-knowledge | `status` (serve reachability, providers, counts), `providers`, `project`, `mcp_pulse`, `config_drift` |
| `opencode_mcpb_install` | Install `.mcpb` bundles into opencode config | unpack manifest, merge server entry, dry-run support |
| `opencode_shutdown` | Graceful self-termination | reason-tagged shutdown for agents |

Prefab cards (`app=True`) on runs/status/sessions list tools render in-chat.
MCP endpoint: `/mcp` on the unified backend (:10951) or stdio via `just serve`.
REST mirrors live under `/api/*` (see `docs/USAGE.md` and `GET /docs` on a running
backend).
