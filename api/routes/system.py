import asyncio
import os
import platform
import threading

import httpx
from fastapi import APIRouter

router = APIRouter(tags=["system"])


def _get_gpu_name() -> str:
    try:
        import subprocess

        r = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_VideoController | Select-Object -First 1 -ExpandProperty Name",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _get_cpu_percent() -> float:
    try:
        import psutil

        return psutil.cpu_percent(interval=0.3)
    except ImportError:
        return 0.0


def _get_memory() -> dict:
    try:
        import psutil

        m = psutil.virtual_memory()
        return {"total": m.total, "used": m.used, "percent": m.percent}
    except ImportError:
        return {"total": 0, "used": 0, "percent": 0.0}


@router.post("/shutdown")
async def shutdown():
    """Self-termination endpoint (TOOL_DESIGN_STANDARDS SS1E).

    Unconditional on purpose: this is the REST mirror of the
    opencode_shutdown MCP tool. No confirm flag - the API is bound to
    loopback/CORS-restricted origins.
    """
    threading.Timer(0.5, lambda: os._exit(0)).start()
    return {"success": True, "message": "Server shutting down..."}


@router.get("/system")
async def system_info():
    cpu = _get_cpu_percent()
    mem = _get_memory()
    gpu = _get_gpu_name()
    return {
        "success": True,
        "data": {
            "cpu": cpu,
            "memory": mem,
            "platform": platform.system(),
            "gpu": gpu,
        },
    }


@router.get("/llm/providers")
async def llm_providers():
    providers = []
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://127.0.0.1:11434/api/tags")
            if resp.status_code == 200:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                providers.append(
                    {
                        "id": "ollama",
                        "label": "Ollama",
                        "base_url": "http://127.0.0.1:11434/v1",
                        "models": models,
                        "needs_key": False,
                    }
                )
    except Exception:
        providers.append(
            {
                "id": "ollama",
                "label": "Ollama",
                "base_url": "http://127.0.0.1:11434/v1",
                "models": [],
                "needs_key": False,
            }
        )
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://127.0.0.1:1234/v1/models")
            if resp.status_code == 200:
                data = resp.json()
                models = [m["id"] for m in data.get("data", [])]
                providers.append(
                    {
                        "id": "lmstudio",
                        "label": "LM Studio",
                        "base_url": "http://127.0.0.1:1234/v1",
                        "models": models,
                        "needs_key": False,
                    }
                )
    except Exception:
        providers.append(
            {
                "id": "lmstudio",
                "label": "LM Studio",
                "base_url": "http://127.0.0.1:1234/v1",
                "models": [],
                "needs_key": False,
            }
        )
    return {"success": True, "data": {"providers": providers}}


@router.get("/ollama/status")
async def ollama_status():
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", 11434), timeout=1.0)
        writer.close()
        await writer.wait_closed()
        return {"success": True, "data": {"running": True, "port": 11434, "provider": "ollama"}}
    except Exception:
        pass
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", 1234), timeout=1.0)
        writer.close()
        await writer.wait_closed()
        return {"success": True, "data": {"running": True, "port": 1234, "provider": "lmstudio"}}
    except Exception:
        return {"success": True, "data": {"running": False, "port": None, "provider": None}}


@router.get("/ollama/models")
async def ollama_models():
    """Fetch available models from Ollama or LM Studio."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Try Ollama first (port 11434)
        try:
            r = await client.get("http://127.0.0.1:11434/api/tags")
            if r.is_success:
                models = [m["name"] for m in r.json().get("models", [])]
                return {
                    "success": True,
                    "data": {
                        "provider": "ollama",
                        "port": 11434,
                        "models": models,
                    },
                }
        except Exception:
            pass

        # Try LM Studio (port 1234, OpenAI-compatible /v1/models)
        try:
            r = await client.get("http://127.0.0.1:1234/v1/models")
            if r.is_success:
                models = [m["id"] for m in r.json().get("data", [])]
                return {
                    "success": True,
                    "data": {
                        "provider": "lmstudio",
                        "port": 1234,
                        "models": models,
                    },
                }
        except Exception:
            pass

        return {
            "success": False,
            "data": {
                "provider": None,
                "port": None,
                "models": [],
            },
        }
