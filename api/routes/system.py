import asyncio
import platform

from fastapi import APIRouter

router = APIRouter(tags=["system"])


def _get_gpu_name() -> str:
    try:
        import subprocess
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_VideoController | Select-Object -First 1 -ExpandProperty Name"],
            capture_output=True, text=True, timeout=5,
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


@router.get("/ollama/status")
async def ollama_status():
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", 11434), timeout=1.0
        )
        writer.close()
        await writer.wait_closed()
        return {"success": True, "data": {"running": True, "port": 11434, "provider": "ollama"}}
    except Exception:
        pass
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", 1234), timeout=1.0
        )
        writer.close()
        await writer.wait_closed()
        return {"success": True, "data": {"running": True, "port": 1234, "provider": "lmstudio"}}
    except Exception:
        return {"success": True, "data": {"running": False, "port": None, "provider": None}}
