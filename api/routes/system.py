import asyncio
import logging
import os
import platform
import threading

import httpx
from fastapi import APIRouter

router = APIRouter(tags=["system"])

logger = logging.getLogger(__name__)


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
    except Exception as e:
        logger.debug("[system] GPU probe failed: %s", e)
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
@router.get("/llm/discover")
async def ollama_status():
    """LLM liveness probe (canonical alias: GET /api/llm/discover)."""
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", 11434), timeout=1.0)
        writer.close()
        await writer.wait_closed()
        return {"success": True, "data": {"running": True, "port": 11434, "provider": "ollama"}}
    except Exception as e:
        logger.debug("[system] ollama probe :11434 failed: %s", e)
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", 1234), timeout=1.0)
        writer.close()
        await writer.wait_closed()
        return {"success": True, "data": {"running": True, "port": 1234, "provider": "lmstudio"}}
    except Exception as e:
        logger.debug("[system] lmstudio probe :1234 failed: %s", e)
        return {"success": True, "data": {"running": False, "port": None, "provider": None}}


@router.get("/ollama/models")
@router.get("/llm/models")
async def ollama_models():
    """Fetch available models from Ollama or LM Studio (canonical alias: GET /api/llm/models)."""
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


@router.get("/llm/onboarding")
async def llm_onboarding():
    """Fresh-install starter facts (WEBAPP_SOTA_STANDARDS VI).

    Live data only: provider liveness (TCP probe, same as /llm/discover),
    GPU name, and the recommended first provider + concrete next step.
    Consumed by the under-hero onboarding cue.
    """
    running: dict[str, bool] = {}
    for port in (11434, 1234):
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection("127.0.0.1", port), timeout=1.0)
            writer.close()
            await writer.wait_closed()
            running[str(port)] = True
        except Exception as e:
            logger.debug("[system] onboarding probe :%d failed: %s", port, e)
            running[str(port)] = False
    gpu = _get_gpu_name()
    if running.get("11434"):
        recommended = "ollama"
    elif running.get("1234"):
        recommended = "lmstudio"
    else:
        recommended = "ollama"
    return {
        "success": True,
        "message": "LLM onboarding facts",
        "data": {
            "ollama_running": running.get("11434", False),
            "lmstudio_running": running.get("1234", False),
            "gpu": gpu,
            "recommended_provider": recommended,
            "next_step": (
                "Pick the recommended provider in Settings and choose a model."
                if any(running.values())
                else "Install Ollama (https://ollama.ai) and pull a model, e.g. `ollama pull llama3.2`."
            ),
        },
    }
