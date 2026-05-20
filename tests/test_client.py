from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from opencode_cli_mcp.client import OpencodeClient


def _mock_response(status_code=200, json_data=None):
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status_code
    mock.is_success = 200 <= status_code < 300
    mock.json.return_value = json_data or {}
    mock.raise_for_status = MagicMock()
    if status_code >= 400:
        mock.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock
        )
    return mock


@pytest.fixture
def client():
    return OpencodeClient("http://127.0.0.1:4096")


@pytest.mark.asyncio
async def test_ping_success(client):
    mock_resp = _mock_response(200, {"status": "ok"})
    with patch.object(client._http, "get", AsyncMock(return_value=mock_resp)):
        result = await client._ping()
    assert result is True


@pytest.mark.asyncio
async def test_ping_failure(client):
    with patch.object(client._http, "get", AsyncMock(side_effect=Exception("refused"))):
        result = await client._ping()
    assert result is False


@pytest.mark.asyncio
async def test_get_health(client):
    mock_resp = _mock_response(200, {"status": "ok"})
    with patch.object(client._http, "get", AsyncMock(return_value=mock_resp)):
        result = await client.get_health()
    assert result == {"status": "ok"}


@pytest.mark.asyncio
async def test_get_health_error(client):
    mock_resp = _mock_response(500)
    with patch.object(client._http, "get", AsyncMock(return_value=mock_resp)):
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_health()


@pytest.mark.asyncio
async def test_list_sessions(client):
    mock_resp = _mock_response(200, {"sessions": [{"id": "s1"}, {"id": "s2"}]})
    with patch.object(client._http, "get", AsyncMock(return_value=mock_resp)):
        result = await client.list_sessions()
    assert result == [{"id": "s1"}, {"id": "s2"}]


@pytest.mark.asyncio
async def test_list_sessions_empty(client):
    mock_resp = _mock_response(200, {"sessions": []})
    with patch.object(client._http, "get", AsyncMock(return_value=mock_resp)):
        result = await client.list_sessions()
    assert result == []


@pytest.mark.asyncio
async def test_get_session(client):
    mock_resp = _mock_response(200, {"id": "abc", "title": "test"})
    with patch.object(client._http, "get", AsyncMock(return_value=mock_resp)) as mock_get:
        result = await client.get_session("abc")
    assert result == {"id": "abc", "title": "test"}
    mock_get.assert_called_once_with("/session/abc")


@pytest.mark.asyncio
async def test_export_session(client):
    mock_resp = _mock_response(200, {"export": "data"})
    with patch.object(client._http, "get", AsyncMock(return_value=mock_resp)):
        result = await client.export_session("abc")
    assert result == {"export": "data"}


@pytest.mark.asyncio
async def test_get_config(client):
    mock_resp = _mock_response(200, {"providers": {"openai": {}}})
    with patch.object(client._http, "get", AsyncMock(return_value=mock_resp)):
        result = await client.get_config()
    assert result == {"providers": {"openai": {}}}


@pytest.mark.asyncio
async def test_list_providers(client):
    mock_resp = _mock_response(200, [{"name": "openai"}])
    with patch.object(client._http, "get", AsyncMock(return_value=mock_resp)):
        result = await client.list_providers()
    assert result == [{"name": "openai"}]


@pytest.mark.asyncio
async def test_get_project(client):
    mock_resp = _mock_response(200, {"path": "/home/user/proj"})
    with patch.object(client._http, "get", AsyncMock(return_value=mock_resp)):
        result = await client.get_project()
    assert result == {"path": "/home/user/proj"}


@pytest.mark.asyncio
async def test_send_message(client):
    mock_resp = _mock_response(200, {"response": "ok"})
    with patch.object(client._http, "post", AsyncMock(return_value=mock_resp)) as mock_post:
        result = await client.send_message("abc", "hello")
    assert result == {"response": "ok"}
    mock_post.assert_called_once_with("/message/abc", json={"message": "hello"})


@pytest.mark.asyncio
async def test_get_messages(client):
    mock_resp = _mock_response(200, [{"role": "user", "content": "hi"}])
    with patch.object(client._http, "get", AsyncMock(return_value=mock_resp)) as mock_get:
        result = await client.get_messages("abc", limit=10)
    assert result == [{"role": "user", "content": "hi"}]
    mock_get.assert_called_once_with("/session/abc/messages", params={"limit": 10})


@pytest.mark.asyncio
async def test_get_messages_default_limit(client):
    mock_resp = _mock_response(200, [])
    with patch.object(client._http, "get", AsyncMock(return_value=mock_resp)) as mock_get:
        await client.get_messages("abc")
    mock_get.assert_called_once_with("/session/abc/messages", params={"limit": 50})


@pytest.mark.asyncio
async def test_get_session_diff(client):
    mock_resp = _mock_response(200, {"created": ["a.py"], "modified": ["b.py"], "deleted": []})
    with patch.object(client._http, "get", AsyncMock(return_value=mock_resp)):
        result = await client.get_session_diff("abc")
    assert result == {"created": ["a.py"], "modified": ["b.py"], "deleted": []}


@pytest.mark.asyncio
async def test_get_session_files(client):
    mock_resp = _mock_response(200, [{"path": "a.py", "change_type": "modified"}])
    with patch.object(client._http, "get", AsyncMock(return_value=mock_resp)):
        result = await client.get_session_files("abc")
    assert result == [{"path": "a.py", "change_type": "modified"}]


@pytest.mark.asyncio
async def test_get_server_status(client):
    mock_health = _mock_response(200, {"status": "ok"})
    mock_sessions = _mock_response(200, {"sessions": [{"id": "s1"}, {"id": "s2"}]})
    mock_config = _mock_response(200, {"defaultProvider": "openai"})
    with patch.object(client._http, "get", AsyncMock(side_effect=[mock_health, mock_sessions, mock_config])):
        result = await client.get_server_status()
    assert result["health"]["status"] == "ok"
    assert result["sessions"] == 2
    assert result["config"]["defaultProvider"] == "openai"


@pytest.mark.asyncio
async def test_get_server_status_partial_failure(client):
    mock_health = _mock_response(200, {"status": "ok"})
    with patch.object(client._http, "get", AsyncMock(side_effect=[mock_health, Exception("fail"), Exception("fail")])):
        result = await client.get_server_status()
    assert result["health"]["status"] == "ok"
    assert result["sessions"] == -1
    assert result["config"] == {}


@pytest.mark.asyncio
async def test_base_url_trailing_slash():
    client = OpencodeClient("http://127.0.0.1:4096/")
    assert client.base_url == "http://127.0.0.1:4096"


@pytest.mark.asyncio
async def test_ensure_server_when_running(client):
    with patch.object(client, "_ping", AsyncMock(return_value=True)):
        result = await client.ensure_server()
    assert result is True


@pytest.mark.asyncio
async def test_ensure_server_starts_when_down(client):
    with patch.object(client, "_ping", AsyncMock(side_effect=[False, True])):
        with patch.object(client, "_start_server", AsyncMock(return_value=True)):
            result = await client.ensure_server()
    assert result is True


@pytest.mark.asyncio
async def test_ensure_server_fails(client):
    with patch.object(client, "_ping", AsyncMock(return_value=False)):
        with patch.object(client, "_start_server", AsyncMock(return_value=False)):
            result = await client.ensure_server()
    assert result is False


@pytest.mark.asyncio
async def test_close(client):
    client._process = MagicMock()
    await client.close()
    client._process.terminate.assert_called_once()
