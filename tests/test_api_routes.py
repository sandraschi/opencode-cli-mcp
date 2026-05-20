"""Tests for FastAPI backend routes using TestClient.

Proxy routes (/api/opencode/*, /api/runs/*) are tested lightly since they
depend on an external opencode serve process.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from opencode_cli_mcp.registry import TOOL_DEFINITIONS

client = TestClient(app)


class TestCapabilities:
    def test_capabilities_ok(self):
        resp = client.get("/api/capabilities")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["server"]["name"] == "opencode-cli-mcp"
        assert data["tool_surface"]["total"] == 14

    def test_health(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "opencode-cli-mcp-api"

    def test_v1_health(self):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


class TestTools:
    def test_list_tools(self):
        resp = client.get("/api/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]["tools"]) == 14

    def test_tool_names_match_registry(self):
        resp = client.get("/api/tools")
        data = resp.json()
        api_names = {t["name"] for t in data["data"]["tools"]}
        reg_names = {t["name"] for t in TOOL_DEFINITIONS}
        assert api_names == reg_names


class TestDocs:
    def test_list_docs(self):
        resp = client.get("/api/docs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        docs_list = data["data"]["docs"]
        assert len(docs_list) >= 2
        ids = {d["id"] for d in docs_list}
        assert "README" in ids

    def test_get_doc(self):
        resp = client.get("/api/docs/README")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "opencode" in data["data"]["content"].lower()

    def test_get_doc_not_found(self):
        resp = client.get("/api/docs/nonexistent-doc-id")
        assert resp.status_code == 404

    def test_get_doc_usages(self):
        resp = client.get("/api/docs/USAGE")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "Quick Reference" in data["data"]["content"]

    def test_get_doc_claude(self):
        resp = client.get("/api/docs/CLAUDE")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True


class TestOpenCodeTools:
    def test_list_tools(self):
        resp = client.get("/api/opencode-tools")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        tools = data["data"]["tools"]
        assert len(tools) >= 4
        names = {t["name"] for t in tools}
        assert "fleet" in names
        assert "sessions" in names
        assert "system" in names
        for t in tools:
            assert "source" in t
            assert len(t["source"]) > 50

    def test_get_single_tool(self):
        resp = client.get("/api/opencode-tools/fleet")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["name"] == "fleet"
        assert "import { tool }" in data["data"]["source"]

    def test_get_tool_not_found(self):
        resp = client.get("/api/opencode-tools/nonexistent")
        assert resp.status_code == 404


class TestFleet:
    def test_fleet_response_structure(self):
        resp = client.get("/api/fleet")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        apps = data["data"]["apps"]
        assert isinstance(apps, list)
        if apps:
            for app in apps:
                assert "port" in app
                assert "alive" in app
                assert "name" in app


class TestSystem:
    def test_system_info(self):
        resp = client.get("/api/system")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "cpu" in data["data"]
        assert "memory" in data["data"]
        assert "platform" in data["data"]

    def test_ollama_status(self):
        resp = client.get("/api/ollama/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "running" in data["data"]


class TestSettings:
    def test_get_settings(self):
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert "theme" in data
        assert "llm_provider" in data
        assert "local_endpoint" in data

    def test_update_settings(self):
        original = client.get("/api/settings").json()
        update = {"theme": "dark", "local_model": "test-model"}
        resp = client.put("/api/settings", json=update)
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        current = client.get("/api/settings").json()
        assert current["local_model"] == "test-model"
        client.put("/api/settings", json={"local_model": original.get("local_model", "")})

    def test_empty_update(self):
        resp = client.put("/api/settings", json={})
        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestProxy:
    @pytest.fixture(autouse=True)
    def _mock_opencode(self):
        mock_client = AsyncMock()
        mock_client.ensure_server = AsyncMock(return_value=True)
        mock_client.close = AsyncMock()
        mock_client.get_server_status = AsyncMock(return_value={
            "health": {"status": "ok"},
            "sessions": 3,
            "config": {},
        })
        mock_client.list_sessions = AsyncMock(return_value=[
            {"id": "s1", "title": "test"},
            {"id": "s2"},
        ])
        mock_client.get_session = AsyncMock(return_value={"id": "s1", "title": "test"})
        mock_client.get_session_diff = AsyncMock(return_value={"created": ["a.py"]})
        mock_client.get_session_files = AsyncMock(return_value=[{"path": "a.py"}])

        with patch("api.routes.proxy.OpencodeClient", return_value=mock_client):
            yield

    def test_status_endpoint(self):
        resp = client.get("/api/opencode/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    def test_sessions_endpoint(self):
        resp = client.get("/api/opencode/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert len(data["data"]["sessions"]) == 2

    def test_session_detail(self):
        resp = client.get("/api/opencode/sessions/s1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["session"]["id"] == "s1"

    def test_session_diff(self):
        resp = client.get("/api/opencode/sessions/s1/diff")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["diff"]["created"] == ["a.py"]

    def test_session_files(self):
        resp = client.get("/api/opencode/sessions/s1/files")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["files"] == [{"path": "a.py"}]


class TestCORS:
    def test_cors_headers(self):
        resp = client.options(
            "/api/capabilities",
            headers={
                "Origin": "http://localhost:10950",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.status_code == 200
        assert "access-control-allow-origin" in resp.headers


class TestNotFound:
    def test_404_on_unknown_route(self):
        resp = client.get("/api/this-does-not-exist")
        assert resp.status_code == 404
