import asyncio

from fastapi import APIRouter

router = APIRouter(tags=["fleet"])

FLEET_PORTS = [
    10700, 10702, 10704, 10706, 10708, 10710, 10714, 10718, 10720,
    10724, 10728, 10730, 10738, 10740, 10742, 10746, 10748, 10750,
    10756, 10762, 10764, 10766, 10768, 10770, 10772, 10774, 10776,
    10778, 10780, 10788, 10792, 10794, 10796, 10798, 10800, 10802,
    10804, 10806, 10810, 10812, 10814, 10816, 10818, 10820, 10822,
    10826, 10828, 10830, 10832, 10834, 10836, 10838, 10840, 10842,
    10844, 10848, 10850, 10852, 10858, 10860, 10862, 10864, 10870,
    10874, 10876, 10878, 10880, 10882, 10884, 10886, 10888, 10892,
    10894, 10896, 10898, 10900, 10901, 10922, 10924, 10927, 10928,
    10930, 10932, 10940, 10942, 10946, 10948, 10950, 10951,
]

FLEET_LABELS: dict[int, str] = {
    10700: "virtualization-mcp",
    10704: "advanced-memory-mcp",
    10720: "calibre-mcp",
    10740: "plex-mcp",
    10770: "arxiv-mcp",
    10794: "documentation-mcp",
    10860: "system-admin-mcp",
    10950: "opencode-cli-mcp",
}


async def _probe(port: int) -> bool:
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", port), timeout=0.5
        )
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


@router.get("/fleet")
async def list_fleet():
    results = []
    for port in FLEET_PORTS:
        alive = await _probe(port)
        results.append({
            "port": port,
            "alive": alive,
            "label": FLEET_LABELS.get(port, "unknown"),
            "name": FLEET_LABELS.get(port, f"service-{port}"),
        })
    return {"success": True, "data": {"apps": results}}


@router.get("/ollama/status")
async def ollama_status():
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", 11434), timeout=1.0
        )
        writer.close()
        await writer.wait_closed()
        return {"success": True, "data": {"running": True, "models": []}}
    except Exception:
        return {"success": True, "data": {"running": False, "models": []}}


@router.get("/system")
async def system_info():
    import psutil
    mem = psutil.virtual_memory()
    gpu = "unknown"
    try:
        import subprocess
        r = subprocess.run(
            ["wmic", "path", "win32_VideoController", "get", "name"],
            capture_output=True, text=True, timeout=3
        )
        lines = [ln.strip() for ln in r.stdout.split("\n") if ln.strip() and "name" not in ln.lower()]  # noqa: E501
        if lines:
            gpu = lines[0]
    except Exception:
        pass
    return {
        "success": True,
        "data": {
            "cpu": psutil.cpu_percent(interval=0.3),
            "memory": {
                "total": mem.total,
                "used": mem.used,
                "percent": mem.percent,
            },
            "platform": __import__("sys").platform,
            "gpu": gpu,
        },
    }
