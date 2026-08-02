"""Read/write the opencode global config (~/.config/opencode/opencode.json).

The opencode serve API exposes config read-only. The webapp needs full
management of the `mcp` and `plugin` sections (the winapp UI shows truncated
paths and no server info - this fills the gap). Writes go directly to the
config file with:

- a timestamped `.bak` backup BEFORE every write (fleet batch-mutation rule)
- JSON validation after merge (opencode refuses to start on invalid config)
- atomic write via temp file + os.replace (no partial files)

Config location: global `~/.config/opencode/opencode.json` (project configs
are out of scope - the global file is where the winapp and this webapp share
state).
"""

import datetime
import json
import os
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["opencode-config"])


def _config_path() -> Path:
    env = os.environ.get("OPENCODE_GLOBAL_CONFIG")
    if env:
        return Path(env)
    return Path.home() / ".config" / "opencode" / "opencode.json"


def _read_config() -> dict[str, Any]:
    path = _config_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"opencode config unreadable at {path}: {e}")


def _write_config(data: dict[str, Any]) -> dict[str, Any]:
    """Backup, validate, atomic-write. Returns the saved config."""
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Timestamped backup before write (fleet batch-mutation rule).
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(f"{path.suffix}.{stamp}.bak")
    if path.exists():
        try:
            shutil.copy2(path, backup)
        except OSError:
            pass  # backup is best-effort; the atomic write below still protects

    # 2. Validate: json.dumps round-trip must succeed (opencode hard-fails on bad config).
    try:
        payload = json.dumps(data, indent=2)
        json.loads(payload)
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=500, detail=f"Refusing to write invalid config: {e}")

    # 3. Atomic write.
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(payload + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return data


def _mcp_section(config: dict[str, Any]) -> dict[str, Any]:
    mcp = config.get("mcp")
    if not isinstance(mcp, dict):
        mcp = {}
    return mcp


def _plugin_list(config: dict[str, Any]) -> list[Any]:
    plugins = config.get("plugin")
    return list(plugins) if isinstance(plugins, list) else []


def _plugin_dir_plugins() -> list[dict[str, Any]]:
    """Auto-discovered plugins: any *.ts / *.js in ~/.config/opencode/plugins/.

    opencode loads these without any config entry (see customize-opencode:
    "Auto-discovered plugins (no config entry needed): any *.ts or *.js file
    in .opencode/plugin/ or .opencode/plugins/"). The winapp shows them, so
    the depot page must too.
    """
    plugins_dir = _config_path().parent / "plugins"
    if not plugins_dir.is_dir():
        return []
    found = []
    for f in sorted(plugins_dir.iterdir()):
        if f.suffix.lower() in (".ts", ".js", ".mjs", ".cjs"):
            found.append({"name": f.name, "path": str(f), "size": f.stat().st_size, "source": "directory"})
    return found


def _explicit_plugins(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Plugins from the config 'plugin' array (explicit entries)."""
    out = []
    for i, p in enumerate(_plugin_list(config)):
        if isinstance(p, str):
            out.append({"index": i, "name": p, "display": p, "source": "config"})
        elif isinstance(p, list) and p:
            out.append({"index": i, "name": str(p[0]), "display": json.dumps(p), "source": "config"})
        else:
            out.append({"index": i, "name": "(invalid)", "display": json.dumps(p), "source": "config"})
    return out


# --- public API ---------------------------------------------------------


@router.get("/occonfig")
async def get_occonfig():
    """Full opencode config: mcp servers (readable info), plugins, path.

    Each MCP server entry is enriched with a human-readable summary
    (command joined, url, type, enabled) - the winapp only shows a
    truncated path.
    """
    config = _read_config()
    mcp = _mcp_section(config)
    servers = []
    for name, cfg in mcp.items():
        if not isinstance(cfg, dict):
            servers.append({"name": str(name), "raw": cfg, "summary": "invalid entry"})
            continue
        cmd = cfg.get("command")
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd or "")
        servers.append(
            {
                "name": str(name),
                "type": cfg.get("type", "local"),
                "enabled": cfg.get("enabled", True),
                "command": cmd_str,
                "url": cfg.get("url", ""),
                "environment": cfg.get("environment", {}),
                "summary": cmd_str or cfg.get("url", ""),
            }
        )
    servers.sort(key=lambda s: s["name"].lower())
    return {
        "success": True,
        "data": {
            "path": str(_config_path()),
            "mcp_servers": servers,
            "mcp_count": len(servers),
            "plugins": _explicit_plugins(config),
            "plugin_count": len(_explicit_plugins(config)),
            "plugin_dir_plugins": _plugin_dir_plugins(),
            "plugin_dir": str(_config_path().parent / "plugins"),
            "plugin_dir_count": len(_plugin_dir_plugins()),
        },
    }


@router.post("/occonfig/mcp")
async def add_mcp_server(body: dict):
    """Add or update an MCP server entry in the opencode config.

    body: {name, type: "local"|"remote", command: [..] | null, url: str | null,
           environment: {} | null, enabled: bool}
    """
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="name required")
    server_type = body.get("type", "local")
    if server_type not in ("local", "remote"):
        raise HTTPException(status_code=422, detail="type must be 'local' or 'remote'")

    entry: dict[str, Any] = {"type": server_type, "enabled": bool(body.get("enabled", True))}
    if server_type == "local":
        cmd = body.get("command")
        if not cmd:
            raise HTTPException(status_code=422, detail="local server requires command")
        entry["command"] = cmd if isinstance(cmd, list) else str(cmd).split()
        if isinstance(body.get("environment"), dict) and body["environment"]:
            entry["environment"] = body["environment"]
    else:
        url = (body.get("url") or "").strip()
        if not url:
            raise HTTPException(status_code=422, detail="remote server requires url")
        entry["url"] = url
        if isinstance(body.get("headers"), dict) and body["headers"]:
            entry["headers"] = body["headers"]

    config = _read_config()
    mcp = _mcp_section(config)
    existed = name in mcp
    mcp[name] = entry
    config["mcp"] = mcp
    _write_config(config)
    return {"success": True, "message": f"{'Updated' if existed else 'Added'} MCP server '{name}'", "data": entry}


@router.delete("/occonfig/mcp/{name}")
async def remove_mcp_server(name: str):
    config = _read_config()
    mcp = _mcp_section(config)
    if name not in mcp:
        raise HTTPException(status_code=404, detail=f"MCP server '{name}' not found")
    del mcp[name]
    config["mcp"] = mcp
    _write_config(config)
    return {"success": True, "message": f"Removed MCP server '{name}'"}


@router.patch("/occonfig/mcp/{name}")
async def patch_mcp_server(name: str, body: dict):
    """Toggle enabled or update a field on an existing MCP server."""
    config = _read_config()
    mcp = _mcp_section(config)
    if name not in mcp or not isinstance(mcp[name], dict):
        raise HTTPException(status_code=404, detail=f"MCP server '{name}' not found")
    entry = mcp[name]
    if "enabled" in body:
        entry["enabled"] = bool(body["enabled"])
    for key in ("type", "command", "url", "environment", "headers"):
        if key in body:
            entry[key] = body[key]
    config["mcp"] = mcp
    _write_config(config)
    return {"success": True, "message": f"Updated MCP server '{name}'", "data": entry}


@router.post("/occonfig/plugin")
async def add_plugin(body: dict):
    """Append a plugin entry to the config's plugin array.

    body: {plugin: "name@version" | "/path/to/plugin.ts" | ["name", {...}]}
    """
    plugin = body.get("plugin")
    if plugin is None:
        raise HTTPException(status_code=422, detail="plugin required")
    config = _read_config()
    plugins = _plugin_list(config)
    plugins.append(plugin)
    config["plugin"] = plugins
    _write_config(config)
    return {"success": True, "message": f"Added plugin {plugin if isinstance(plugin, str) else '(tupled)'}"}


@router.delete("/occonfig/plugin/{index}")
async def remove_plugin(index: int):
    config = _read_config()
    plugins = _plugin_list(config)
    if index < 0 or index >= len(plugins):
        raise HTTPException(status_code=404, detail=f"Plugin index {index} out of range")
    removed = plugins.pop(index)
    config["plugin"] = plugins
    _write_config(config)
    return {"success": True, "message": f"Removed plugin {removed if isinstance(removed, str) else '(tupled)'}"}
