import asyncio
import atexit
import os
import shutil
import subprocess
from typing import Any
from urllib.parse import urlsplit

import httpx

DEFAULT_SERVE_URL = os.environ.get("OPENCODE_SERVE_URL", "http://127.0.0.1:4096")


def _serve_auth() -> httpx.BasicAuth | None:
    """Basic auth for password-protected opencode serve (desktop app env).

    The opencode desktop app sets OPENCODE_SERVER_PASSWORD in the environment,
    inherited by every child process - including our spawned `opencode serve` -
    and a password-protected serve returns 401 without Basic auth. Read the
    env lazily (not at import) so a desktop app that sets the password after
    our backend starts is still picked up.
    """
    password = os.environ.get("OPENCODE_SERVER_PASSWORD", "")
    if password:
        username = os.environ.get("OPENCODE_SERVER_USERNAME", "opencode")
        return httpx.BasicAuth(username, password)
    return None


def _resolve_binary() -> str:
    """Resolve the opencode CLI binary to a runnable path.

    Windows CreateProcess only appends .exe when resolving a bare name, so
    npm-installed shims (opencode.cmd / opencode.ps1) were never found and
    autostart silently failed. shutil.which() honors PATHEXT (.exe/.cmd/.bat)
    and returns the actual runnable file.
    """
    env_override = os.environ.get("OPENCODE_BINARY")
    if env_override:
        return env_override
    resolved = shutil.which("opencode")
    if resolved:
        return resolved
    return "opencode"  # last resort; Popen will raise FileNotFoundError


OPENCODE_BINARY = _resolve_binary()


class OpencodeClient:
    """HTTP client for the opencode serve API.

    Prefer the module-level get_client() singleton in tools and routes: it
    reuses one HTTP connection pool and spawns at most one `opencode serve`
    process per Python process. The old per-call pattern (instantiate, use,
    close) cold-started opencode serve and then killed it again on every
    single tool call whenever serve was not already running.
    """

    def __init__(self, base_url: str = DEFAULT_SERVE_URL):
        self.base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=30.0, auth=_serve_auth())
        self._process: subprocess.Popen | None = None
        self._start_lock: asyncio.Lock | None = None

    @property
    def port(self) -> int:
        """Port derived from base_url so autostart honors OPENCODE_SERVE_URL."""
        try:
            return urlsplit(self.base_url).port or 4096
        except ValueError:
            return 4096

    async def ensure_server(self) -> bool:
        if await self._ping():
            return True
        if self._start_lock is None:
            self._start_lock = asyncio.Lock()
        async with self._start_lock:
            # Re-check: another caller may have started serve while we waited.
            if await self._ping():
                return True
            return await self._start_server()

    async def _ping(self) -> bool:
        try:
            r = await self._http.get("/global/health", timeout=3.0)
            return r.is_success
        except Exception:
            return False

    async def _start_server(self) -> bool:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            self._process = subprocess.Popen(
                [OPENCODE_BINARY, "serve", "--port", str(self.port)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
        except FileNotFoundError:
            return False
        atexit.register(self._terminate_spawned)
        for _ in range(30):
            if await self._ping():
                return True
            await asyncio.sleep(0.5)
        return False

    def _terminate_spawned(self):
        """atexit hook: don't leave a spawned opencode serve orphaned."""
        proc = self._process
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
            except OSError:
                pass

    async def close(self):
        """Explicit teardown: close the HTTP pool and stop a spawned serve.

        Do NOT call this per tool call on the shared client - it exists for
        tests and deliberate shutdown only.
        """
        await self._http.aclose()
        if self._process:
            self._process.terminate()

    async def get_health(self) -> dict[str, Any]:
        r = await self._http.get("/global/health")
        r.raise_for_status()
        return r.json()

    async def list_sessions(self) -> list[dict[str, Any]]:
        r = await self._http.get("/session")
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else data.get("sessions", [])

    async def get_session(self, session_id: str) -> dict[str, Any]:
        r = await self._http.get(f"/session/{session_id}")
        r.raise_for_status()
        return r.json()

    async def get_config(self) -> dict[str, Any]:
        r = await self._http.get("/config")
        r.raise_for_status()
        return r.json()

    async def list_providers(self) -> list[dict[str, Any]]:
        r = await self._http.get("/provider")
        r.raise_for_status()
        return r.json()

    async def get_project(self) -> dict[str, Any]:
        r = await self._http.get("/project/current")
        r.raise_for_status()
        return r.json()

    async def send_message(self, session_id: str, message: str) -> dict[str, Any]:
        r = await self._http.post(
            f"/session/{session_id}/message",
            json={"parts": [{"type": "text", "text": message}]},
        )
        r.raise_for_status()
        return r.json()

    async def get_messages(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        r = await self._http.get(f"/session/{session_id}/message", params={"limit": limit})
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, list) else data.get("items", [])

    async def get_session_diff(self, session_id: str) -> dict[str, Any]:
        r = await self._http.get(f"/session/{session_id}/diff")
        r.raise_for_status()
        return r.json()

    async def get_server_status(self) -> dict[str, Any]:
        result = {}
        try:
            result["health"] = await self.get_health()
        except Exception:
            result["health"] = {"status": "unreachable"}
        try:
            result["sessions"] = len(await self.list_sessions())
        except Exception:
            result["sessions"] = -1
        try:
            result["config"] = await self.get_config()
        except Exception:
            result["config"] = {}
        return result

    async def get_mcp_status(self) -> dict[str, Any]:
        """Per-server MCP connection status from opencode serve (GET /mcp).

        Returns {name: {"status": "connected" | "connecting" | "error" | ...}}.
        Serve probes each configured server, so this can take tens of seconds
        when many servers are down - use a long per-request timeout.
        """
        r = await self._http.get("/mcp", timeout=45.0)
        r.raise_for_status()
        data = r.json()
        return data if isinstance(data, dict) else {}


_shared_client: OpencodeClient | None = None


def get_client() -> OpencodeClient:
    """Process-wide shared client (lazy). Use this in tools and API routes."""
    global _shared_client
    if _shared_client is None:
        _shared_client = OpencodeClient()
    return _shared_client
