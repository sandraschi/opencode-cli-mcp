import pytest
from fastapi.testclient import TestClient

from api.main import app
from opencode_cli_mcp import request_log


@pytest.fixture(autouse=True)
def clean_log():
    request_log.reset()
    yield
    request_log.reset()


def test_record_and_snapshot():
    request_log.record("get", "/api/x", 200, 1.5)
    request_log.record("POST", "/api/y", 500, 2.0)
    snap = request_log.snapshot()
    assert snap["count"] == 2
    assert [r["method"] for r in snap["requests"]] == ["GET", "POST"]
    assert snap["requests"][1]["status"] == 500


def test_snapshot_limit_keeps_newest():
    for i in range(10):
        request_log.record("GET", f"/api/{i}", 200, 0.1)
    snap = request_log.snapshot(limit=3)
    assert snap["count"] == 10
    assert [r["path"] for r in snap["requests"]] == ["/api/7", "/api/8", "/api/9"]


def test_is_exempt():
    assert request_log.is_exempt("/api/v1/request-log")
    assert not request_log.is_exempt("/api/depot/sessions")


def test_endpoint_contract_and_self_exemption():
    client = TestClient(app)
    client.get("/api/v1/health")
    first = client.get("/api/v1/request-log").json()
    # Only the health call is counted; polling the log must not inflate it.
    assert first["count"] == 1
    assert first["requests"][0]["path"] == "/api/v1/health"
    client.get("/api/depot/tags")
    second = client.get("/api/v1/request-log").json()
    assert second["count"] == 2
