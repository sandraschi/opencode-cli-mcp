"""Install an MCPB bundle into opencode's config.

Reads an .mcpb file (or unpacked directory), extracts the manifest,
and merges the server definition into ~/.config/opencode/opencode.json
under the mcp section.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field

OPCODE_CONFIG = Path.home() / ".config" / "opencode" / "opencode.json"


def _find_opencode_config() -> Path:
    """Locate opencode config, checking common paths."""
    candidates = [
        Path.home() / ".config" / "opencode" / "opencode.json",
        Path.home() / ".config" / "opencode" / "opencode.jsonc",
        Path.cwd() / "opencode.json",
        Path.cwd() / "opencode.jsonc",
    ]
    for c in candidates:
        if c.exists():
            return c
    return OPCODE_CONFIG


def _read_manifest_from_mcpb(mcpb_path: Path) -> dict[str, Any]:
    """Extract manifest from an .mcpb file by unpacking it."""
    tmp = tempfile.mkdtemp(prefix="opencode-mcpb-")
    try:
        result = subprocess.run(
            ["mcpb", "unpack", str(mcpb_path), tmp],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise ValueError(f"mcpb unpack failed: {result.stderr.strip()}")
        manifest_path = Path(tmp) / "manifest.json"
        if not manifest_path.exists():
            raise ValueError(f"manifest.json not found in {mcpb_path}")
        with open(manifest_path, encoding="utf-8") as f:
            return json.load(f)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _read_manifest_from_dir(dir_path: Path) -> dict[str, Any]:
    """Read manifest from an already-unpacked directory."""
    manifest_path = dir_path / "manifest.json"
    if not manifest_path.exists():
        raise ValueError(f"manifest.json not found in {dir_path}")
    with open(manifest_path, encoding="utf-8") as f:
        return json.load(f)


def _build_server_config(manifest: dict[str, Any]) -> dict[str, Any]:
    """Translate an MCPB manifest into an opencode mcp entry."""
    server = manifest.get("server", {})
    mcp_config = server.get("mcp_config", {})
    command = mcp_config.get("command", "uv")
    args = mcp_config.get("args", [])
    env = mcp_config.get("env", {})

    resolved_args = [a.replace("${PWD}", str(Path.cwd())) for a in args]

    entry: dict[str, Any] = {
        "type": "local",
        "command": [command] + resolved_args,
        "environment": env,
        "enabled": True,
    }

    timeout = mcp_config.get("timeout")
    if timeout is not None:
        entry["timeout"] = timeout

    return entry


async def opencode_mcpb_install(
    source: Annotated[
        str,
        Field(description="Path to an .mcpb file or an unpacked MCPB directory."),
    ],
    name_override: Annotated[
        str | None,
        Field(description="Override the server name in opencode config. Default: from manifest."),
    ] = None,
    dry_run: Annotated[
        bool,
        Field(description="Show what would be written without modifying the config."),
    ] = False,
) -> dict[str, Any]:
    """OPENCODE_MCPB_INSTALL - Install an MCPB bundle into opencode config.

    Unpacks the .mcpb (or reads an unpacked directory), extracts the manifest,
    and merges the server definition into the opencode config file's `mcp` section.

    ## Return Format
    {"success": bool, "server_name": str, "config_path": str, "entry": {...}}

    ## Examples
    opencode_mcpb_install(source="./dist/arxiv-mcp-v1.0.0.mcpb")
    opencode_mcpb_install(source="./dist/arxiv-mcp-v1.0.0.mcpb", name_override="arxiv")
    opencode_mcpb_install(source="./mcpb/", dry_run=True)
    """
    src_path = Path(source).expanduser().resolve()
    if not src_path.exists():
        return {
            "success": False,
            "error": f"Source not found: {src_path}",
            "recovery_options": ["Check the path and try again."],
        }

    if src_path.is_file() and src_path.suffix == ".mcpb":
        manifest = _read_manifest_from_mcpb(src_path)
    elif src_path.is_dir():
        manifest = _read_manifest_from_dir(src_path)
    else:
        return {
            "success": False,
            "error": f"Unrecognized source: {src_path} (must be .mcpb file or directory)",
        }

    server_name = name_override or manifest.get("name", "unknown-server")
    new_entry = _build_server_config(manifest)

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "server_name": server_name,
            "entry": new_entry,
            "would_write_to": str(_find_opencode_config()),
        }

    config_path = _find_opencode_config()
    if not config_path.exists():
        # Create minimal config with just the new entry
        config: dict[str, Any] = {"mcp": {server_name: new_entry}}
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return {
            "success": True,
            "server_name": server_name,
            "config_path": str(config_path),
            "created": True,
            "entry": new_entry,
        }

    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    if "mcp" not in config:
        config["mcp"] = {}

    if server_name in config["mcp"]:
        config["mcp"][server_name] = new_entry
        overwritten = True
    else:
        config["mcp"][server_name] = new_entry
        overwritten = False

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    return {
        "success": True,
        "server_name": server_name,
        "config_path": str(config_path),
        "overwritten": overwritten,
        "entry": new_entry,
    }
