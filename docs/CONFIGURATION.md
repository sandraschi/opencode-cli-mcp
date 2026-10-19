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
| `OPENCODE_SERVE_URL` | `http://127.0.0.1:4097` | Serve to talk to (dedicated port; 4096 is the desktop app's locked serve) |
| `OPENCODE_BINARY` | pinned to scoop shim in `fleet-start.config.ps1` (`shutil.which` fallback) | Explicit path wins; required when shims are off PATH (service shells) |
| `OPENCODE_SERVER_PASSWORD` / `OPENCODE_SERVER_USERNAME` | — | Basic auth when talking to a password-protected (desktop) serve |
| `OPENCODE_DB_PATH` | `~/.local/share/opencode/opencode.db` | Depot location override |
| `OPENCODE_CLI_MCP_RAG_ENABLED` | `1` | `0` disables RAG dependencies/endpoints |
| `OPENCODE_CLI_MCP_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Embedding model for the session index |
| `OPENCODE_CLI_MCP_LANCE_DIR` | `%LOCALAPPDATA%/opencode-cli-mcp/lancedb` | Vector index location |
| `OPENCODE_CLI_MCP_BACKUP_INTERVAL_HOURS` | `24` | Autobackup cadence (`0` disables) |
| `OPENCODE_CLI_MCP_PREFAB_APPS` | `1` | `0` skips Prefab card registration |
| `BIND_LAN` | unset (loopback) | `1` binds the backend to `0.0.0.0` for iPad / Tailscale access. **Read the warning below first.** |
| `BIND_HOST` | `127.0.0.1` | Explicit bind address (overrides the `BIND_LAN` default) |
| `FLEET_BIND_HOST` | `127.0.0.1` | Same switch for the fleet launcher (`fleet-start.config.ps1` -> `Backend.Host`) |
| `OPENCODE_CLI_MCP_META_DB` | `~/.local/share/opencode-cli-mcp/meta.db` | Stars/tags sidecar DB (never writes `opencode.db`) |
| `MEMOPS_INBOX_DIR` | `D:\Dev\repos\advanced-memory-mcp\zettelkasten\inbox` | Where `memops` exports are dropped |
| `VITE_PORT` / `VITE_API_TARGET` | set by `start.ps1` | Frontend port + backend URL |

Copy `.env.example` to `.env` for local overrides. `.env` is gitignored and never
bundled (Tauri ships `.env.example` only).

## Remote access from an iPad (Tailscale)

The backend and the Vite dev server both bind loopback by default. That is not a
bug: **this API has no authentication** (CORS/LAN-trust only), so a blind
`0.0.0.0` would expose session delete, export and agent-run endpoints to every
host on the network.

To reach the UI from an iPad over Tailscale:

```powershell
# Backend on all interfaces (explicit opt-in)
$env:FLEET_BIND_HOST = '0.0.0.0'   # or $env:BIND_LAN = '1' for a direct uvicorn run
.\start.ps1
```

Frontend, if you need the dev server rather than the built app:

```powershell
cd web_sota
$env:VITE_API_TARGET = "http://<goliath-tailscale-ip>:10951"
npm run dev -- --host 0.0.0.0 --port 10950
```

Then open `http://<goliath-tailscale-ip>:10950` in Safari. Store it on the Home
Screen for an app-like shell.

Scope the firewall to Tailscale's CGNAT range so this is never reachable from
the LAN or the internet:

```powershell
New-NetFirewallRule -DisplayName "opencode-cli-mcp backend (Tailscale)" `
  -Direction Inbound -Protocol TCP -LocalPort 10951 `
  -RemoteAddress 100.64.0.0/10 -Action Allow
New-NetFirewallRule -DisplayName "opencode-cli-mcp frontend (Tailscale)" `
  -Direction Inbound -Protocol TCP -LocalPort 10950 `
  -RemoteAddress 100.64.0.0/10 -Action Allow
```

Remove with `Remove-NetFirewallRule -DisplayName "opencode-cli-mcp *"`.

For interactive agent sessions (not just browsing the depot), `opencode web`
also serves a browser UI; point it at the same Tailscale address once
`BIND_LAN=1` is in play. RustDesk is then only the fallback.
