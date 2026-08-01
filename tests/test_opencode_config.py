"""Tests for the opencode config management routes (/api/occonfig).

Uses OPENCODE_GLOBAL_CONFIG to point the router at a throwaway config file —
never touches the real ~/.config/opencode/opencode.json.
"""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


@pytest.fixture()
def oc_config(tmp_path: Path):
    cfg_path = tmp_path / "opencode.json"
    cfg_path.write_text(
        json.dumps(
            {
                "$schema": "https://opencode.ai/config.json",
                "model": "deepseek/deepseek-v4-flash",
                "mcp": {
                    "fileops": {
                        "type": "local",
                        "command": ["python", "-m", "filesystem_mcp"],
                    },
                    "gitops": {
                        "type": "local",
                        "command": ["python", "-m", "git_github_mcp"],
                        "enabled": False,
                    },
                },
                "plugin": ["opencode-awesome@1.0.0"],
            }
        ),
        encoding="utf-8",
    )
    # Auto-discovered plugin file
    (tmp_path / "plugins").mkdir()
    (tmp_path / "plugins" / "port-guard.ts").write_text("export default () => ({})", encoding="utf-8")

    os.environ["OPENCODE_GLOBAL_CONFIG"] = str(cfg_path)
    yield cfg_path
    os.environ.pop("OPENCODE_GLOBAL_CONFIG", None)


def test_get_occonfig(oc_config: Path):
    r = client.get("/api/occonfig")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["mcp_count"] == 2
    names = {s["name"] for s in data["mcp_servers"]}
    assert names == {"fileops", "gitops"}
    assert data["mcp_servers"][0]["summary"] == "python -m filesystem_mcp"
    # gitops disabled flag preserved
    gitops = next(s for s in data["mcp_servers"] if s["name"] == "gitops")
    assert gitops["enabled"] is False
    # plugins: 1 explicit + 1 dir-discovered
    assert data["plugin_count"] == 1
    assert data["plugins"][0]["name"] == "opencode-awesome@1.0.0"
    assert data["plugin_dir_count"] == 1
    assert data["plugin_dir_plugins"][0]["name"] == "port-guard.ts"


def test_add_local_mcp(oc_config: Path):
    r = client.post(
        "/api/occonfig/mcp",
        json={
            "name": "resonite-mcp",
            "type": "local",
            "command": ["D:\\repos\\resonite-mcp\\.venv\\Scripts\\python.exe", "-m", "resonite_mcp"],
            "environment": {"RESONITE_URL": "http://127.0.0.1:10979"},
        },
    )
    assert r.status_code == 200
    assert r.json()["success"] is True
    cfg = json.loads(oc_config.read_text())
    assert "resonite-mcp" in cfg["mcp"]
    assert cfg["mcp"]["resonite-mcp"]["environment"]["RESONITE_URL"] == "http://127.0.0.1:10979"
    # backup was created
    backups = list(oc_config.parent.glob("opencode.json.*.bak"))
    assert len(backups) == 1


def test_add_remote_mcp(oc_config: Path):
    r = client.post(
        "/api/occonfig/mcp",
        json={"name": "remote-test", "type": "remote", "url": "http://127.0.0.1:10999/mcp"},
    )
    assert r.status_code == 200
    cfg = json.loads(oc_config.read_text())
    assert cfg["mcp"]["remote-test"]["url"] == "http://127.0.0.1:10999/mcp"
    assert cfg["mcp"]["remote-test"]["type"] == "remote"


def test_add_mcp_validation(oc_config: Path):
    # local without command
    r = client.post("/api/occonfig/mcp", json={"name": "x", "type": "local"})
    assert r.status_code == 422
    # missing name
    r = client.post("/api/occonfig/mcp", json={"type": "local", "command": ["a"]})
    assert r.status_code == 422
    # bad type
    r = client.post("/api/occonfig/mcp", json={"name": "x", "type": "bogus", "command": ["a"]})
    assert r.status_code == 422


def test_patch_enable_disable(oc_config: Path):
    r = client.patch("/api/occonfig/mcp/gitops", json={"enabled": True})
    assert r.status_code == 200
    cfg = json.loads(oc_config.read_text())
    assert cfg["mcp"]["gitops"]["enabled"] is True


def test_remove_mcp(oc_config: Path):
    r = client.delete("/api/occonfig/mcp/fileops")
    assert r.status_code == 200
    cfg = json.loads(oc_config.read_text())
    assert "fileops" not in cfg["mcp"]
    r = client.delete("/api/occonfig/mcp/fileops")
    assert r.status_code == 404


def test_add_plugin(oc_config: Path):
    r = client.post("/api/occonfig/plugin", json={"plugin": "opencode-gemini-auth"})
    assert r.status_code == 200
    cfg = json.loads(oc_config.read_text())
    assert "opencode-gemini-auth" in cfg["plugin"]


def test_remove_plugin(oc_config: Path):
    r = client.delete("/api/occonfig/plugin/0")
    assert r.status_code == 200
    cfg = json.loads(oc_config.read_text())
    assert cfg["plugin"] == []
    r = client.delete("/api/occonfig/plugin/0")
    assert r.status_code == 404


def test_config_backup_created(oc_config: Path):
    client.post("/api/occonfig/mcp", json={"name": "y", "type": "local", "command": ["a"]})
    backups = list(oc_config.parent.glob("opencode.json.*.bak"))
    assert len(backups) == 1
    # backup is the pre-write content (no 'y')
    pre = json.loads(backups[0].read_text())
    assert "y" not in pre["mcp"]
