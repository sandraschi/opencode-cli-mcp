import os
import subprocess
from typing import Any

import httpx

DEFAULT_SERVE_URL = os.environ.get("OPENCODE_SERVE_URL", "http://127.0.0.1:4096")
OPENCODE_BINARY = os.environ.get("OPENCODE_BINARY", "opencode")


class OpencodeClient:
    def __init__(self, base_url: str = DEFAULT_SERVE_URL):
        self.base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        self._process: subprocess.Popen | None = None

    async def ensure_server(self) -> bool:
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
        try:
            self._process = subprocess.Popen(
                [OPENCODE_BINARY, "serve", "--port", "4096"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            for _ in range(30):
                if await self._ping():
                    return True
                await _async_sleep(0.5)
            return False
        except FileNotFoundError:
            return False

    async def close(self):
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
        return r.json().get("sessions", [])

    async def get_session(self, session_id: str) -> dict[str, Any]:
        r = await self._http.get(f"/session/{session_id}")
        r.raise_for_status()
        return r.json()

    async def export_session(self, session_id: str) -> dict[str, Any]:
        r = await self._http.get(f"/session/{session_id}/export")
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
        r = await self._http.get("/project")
        r.raise_for_status()
        return r.json()

    async def send_message(self, session_id: str, message: str) -> dict[str, Any]:
        r = await self._http.post(
            f"/message/{session_id}",
            json={"message": message},
        )
        r.raise_for_status()
        return r.json()

    async def get_messages(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        r = await self._http.get(f"/session/{session_id}/messages", params={"limit": limit})
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


async def _async_sleep(seconds: float):
    import asyncio

    await asyncio.sleep(seconds)
