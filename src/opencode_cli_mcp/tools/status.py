import os

import httpx
import psutil

from opencode_cli_mcp.client import OpencodeClient, get_client


async def _ensure(client: OpencodeClient) -> dict | None:
    if not await client.ensure_server():
        return {"success": False, "message": "opencode serve is not running - start it first", "data": {}}
    return None


async def opencode_server_status() -> dict:
    """Check the status and health of the opencode server. Returns health info, active session count, and config summary."""  # noqa: E501

    client = get_client()
    try:
        err = await _ensure(client)
        if err:
            return err
        status = await client.get_server_status()
        return {
            "success": True,
            "message": "Server status retrieved",
            "data": status,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Could not reach opencode server: {e}",
            "data": {},
        }


async def opencode_list_providers() -> dict:
    """List configured LLM providers in opencode."""  # noqa: E501

    client = get_client()
    err = await _ensure(client)
    if err:
        return err
    providers = await client.list_providers()
    return {
        "success": True,
        "message": f"Found {len(providers)} providers",
        "data": {"providers": providers},
    }


async def opencode_get_project() -> dict:
    """Get the current project context from opencode. Returns the active project path and metadata."""  # noqa: E501

    client = get_client()
    err = await _ensure(client)
    if err:
        return err
    project = await client.get_project()
    return {
        "success": True,
        "message": "Current project retrieved",
        "data": {"project": project},
    }


async def opencode_get_config() -> dict:
    """Read the full opencode configuration. Returns model, provider, MCP server settings, and instructions."""  # noqa: E501

    client = get_client()
    err = await _ensure(client)
    if err:
        return err
    config = await client.get_config()
    return {
        "success": True,
        "message": "Configuration retrieved",
        "data": {"config": config},
    }


async def opencode_get_health() -> dict:
    """Health check for the opencode server. Returns basic connectivity status and uptime."""  # noqa: E501

    client = get_client()
    try:
        health = await client.get_health()
        return {
            "success": True,
            "message": "Server is healthy",
            "data": health,
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Health check failed: {e}",
            "data": {},
        }


def _probe_local(name: str, command: list[str]) -> dict:
    """Check if a local MCP server process is running by matching its command."""
    if not command:
        return {"name": name, "status": "unknown", "detail": "no command configured"}

    cmd_exe = os.path.basename(command[0]).lower()
    for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            pinfo = proc.info
            if not pinfo.get("cmdline"):
                continue
            # Match executable basename against first cmdline arg
            proc_exe = os.path.basename(pinfo["cmdline"][0]).lower()
            if cmd_exe != proc_exe:
                continue
            # Optional: match sub-args for disambiguation (e.g. -m arxiv_mcp)
            if len(command) > 1 and len(pinfo["cmdline"]) > 1:
                cmd_sub = " ".join(str(a).lower() for a in command[1:])
                proc_sub = " ".join(str(a).lower() for a in pinfo["cmdline"][1:])
                if cmd_sub not in proc_sub:
                    continue
            uptime = 0.0
            if pinfo.get("create_time"):
                import time

                uptime = time.time() - pinfo["create_time"]
            return {
                "name": name,
                "status": "alive",
                "pid": pinfo["pid"],
                "detail": f"process running (uptime {uptime:.0f}s)",
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return {"name": name, "status": "dead", "detail": "no matching process found"}


async def _probe_remote(name: str, url: str) -> dict:
    """Check if a remote MCP server URL is reachable."""
    if not url:
        return {"name": name, "status": "unknown", "detail": "no URL configured"}

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(url)
            return {
                "name": name,
                "status": "alive",
                "detail": f"HTTP {r.status_code} from {url}",
            }
        except httpx.ConnectError:
            return {"name": name, "status": "dead", "detail": f"connection refused to {url}"}
        except httpx.TimeoutException:
            return {"name": name, "status": "dead", "detail": f"timeout connecting to {url}"}
        except Exception as e:
            return {"name": name, "status": "dead", "detail": f"error: {e}"}


async def opencode_mcp_pulse() -> dict:
    """Probe every configured MCP server and report alive/dead status.

    Reads the opencode config to discover MCP server definitions, then
    checks each one:
    - Local servers: matched against running processes via psutil
    - Remote servers: HTTP probe to their URL

    Disabled servers are reported as skipped.
    """
    client = get_client()
    err = await _ensure(client)
    if err:
        return err

    config = await client.get_config()
    mcp_servers = (config or {}).get("mcp", {})
    if not isinstance(mcp_servers, dict):
        mcp_servers = {}

    results = []
    alive = 0
    dead = 0
    skipped = 0

    for name, cfg in mcp_servers.items():
        if not isinstance(cfg, dict):
            results.append({"name": str(name), "status": "unknown", "detail": "invalid config entry"})
            skipped += 1
            continue

        if cfg.get("enabled") is False:
            results.append({"name": name, "status": "skipped", "detail": "disabled in config"})
            skipped += 1
            continue

        server_type = cfg.get("type", "local")
        if server_type == "remote":
            result = await _probe_remote(name, cfg.get("url", ""))
        else:
            result = _probe_local(name, cfg.get("command", []))
        results.append(result)
        if result["status"] == "alive":
            alive += 1
        else:
            dead += 1

    return {
        "success": True,
        "message": f"MCP pulse: {alive} alive, {dead} dead/unreachable, {skipped} skipped ({len(results)} total)",
        "data": {
            "servers": results,
            "summary": {
                "total": len(results),
                "alive": alive,
                "dead": dead,
                "skipped": skipped,
            },
        },
        "recovery_options": [
            "Restart dead servers: check logs or restart opencode",
            "Run `opencode_system(action='status')` for more details",
        ],
    }


async def opencode_config_drift() -> dict:
    """Check each local MCP server's configured paths (command, cwd) exist on disk.

    Detects stale config entries where the repo or binary has been moved or deleted.
    """
    import os as _os

    client = get_client()
    err = await _ensure(client)
    if err:
        return err

    config = await client.get_config()
    mcp_servers = (config or {}).get("mcp", {})
    if not isinstance(mcp_servers, dict):
        mcp_servers = {}

    drift_items = []
    ok = 0
    stale = 0
    skipped = 0

    for name, cfg in mcp_servers.items():
        if not isinstance(cfg, dict):
            skipped += 1
            continue
        if cfg.get("enabled") is False:
            skipped += 1
            continue
        server_type = cfg.get("type", "local")
        if server_type != "local":
            skipped += 1
            continue

        command = cfg.get("command", [])
        cwd = cfg.get("cwd")

        issues = []
        if not command or not isinstance(command, list) or not command[0]:
            issues.append("no command configured")
        else:
            exe = command[0]
            if not _os.path.exists(exe):
                # Resolve relative to cwd or check PATH
                resolved = _os.path.expanduser(exe)
                if not _os.path.exists(resolved):
                    issues.append(f"executable not found: {exe}")

        if cwd:
            resolved = _os.path.expanduser(cwd)
            if not _os.path.isdir(resolved):
                issues.append(f"working directory not found: {cwd}")

        item = {
            "name": name,
            "status": "ok" if not issues else "stale",
            "issues": issues,
            "command": command,
            "cwd": cwd or "",
        }
        drift_items.append(item)
        if issues:
            stale += 1
        else:
            ok += 1

    return {
        "success": True,
        "message": (
            f"Config drift: {ok} ok, {stale} stale, {skipped} skipped ({len(drift_items)} local servers checked)"
        ),
        "data": {
            "servers": drift_items,
            "summary": {"total_checked": len(drift_items), "ok": ok, "stale": stale, "skipped": skipped},
        },
    }
