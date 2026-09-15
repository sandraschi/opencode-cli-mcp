# Configuration — opencode-cli-mcp

## Ports (fleet registry)

| Port | Service |
|------|---------|
| 10950 | Frontend (Vite) |
| 10951 | Unified backend (REST `/api/*` + MCP `/mcp`) |
| 4097 | Backend-owned `opencode serve` (autostarted; NOT 4096 — the desktop app's password-locked serve lives there) |

`fleet-start.config.ps1` is the source of truth for ports and the uvicorn target
(`api.main:app`). Never point uvicorn at `opencode_cli_mcp.server:app` (raw FastMCP,
not ASGI-callable — every request 500s).

## Environment variables

| Var | Default | Purpose |
|-----|---------|---------|
| `OPENCODE_SERVE_URL` | `http://127.0.0.1:4096` | Serve to talk to; backend sets 4097 for its own |
| `OPENCODE_BINARY` | resolved via `shutil.which` | Override path to the `opencode` CLI |
| `OPENCODE_SERVER_PASSWORD` / `OPENCODE_SERVER_USERNAME` | — | Basic auth when talking to a password-protected (desktop) serve |
| `OPENCODE_DB_PATH` | `~/.local/share/opencode/opencode.db` | Depot location override |
| `OPENCODE_CLI_MCP_RAG_ENABLED` | `1` | `0` disables RAG dependencies/endpoints |
| `OPENCODE_CLI_MCP_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Embedding model for the session index |
| `OPENCODE_CLI_MCP_LANCE_DIR` | `%LOCALAPPDATA%/opencode-cli-mcp/lancedb` | Vector index location |
| `OPENCODE_CLI_MCP_BACKUP_INTERVAL_HOURS` | `24` | Autobackup cadence (`0` disables) |
| `OPENCODE_CLI_MCP_PREFAB_APPS` | `1` | `0` skips Prefab card registration |
| `VITE_PORT` / `VITE_API_TARGET` | set by `start.ps1` | Frontend port + backend URL |

Copy `.env.example` to `.env` for local overrides. `.env` is gitignored and never
bundled (Tauri ships `.env.example` only).
