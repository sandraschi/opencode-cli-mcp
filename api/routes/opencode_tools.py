from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["opencode-tools"])

TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / ".opencode" / "tools"

KNOWN_TOOL_META = {
    "fleet": {"label": "Fleet Status & Launch", "category": "Fleet", "desc": "Check fleet server status and launch"},
    "sessions": {"label": "Session Management", "category": "Sessions", "desc": "List/inspect opencode sessions"},
    "runs": {"label": "Run Tracking", "category": "Runs", "desc": "List and inspect background agent runs"},
    "system": {"label": "System Resources", "category": "System", "desc": "CPU, memory, GPU, platform diagnostics"},
    "providers": {"label": "Provider & Health", "category": "System", "desc": "LLM provider list and server health"},
    "tools": {"label": "MCP Tool Discovery", "category": "Meta", "desc": "List all MCP tools the server exposes"},
}


def _scan_tools() -> list[dict]:
    items = []
    if not TOOLS_DIR.is_dir():
        return items
    for f in sorted(TOOLS_DIR.iterdir()):
        if f.suffix != ".ts":
            continue
        stem = f.stem
        meta = KNOWN_TOOL_META.get(stem, {"label": stem, "category": "Other", "desc": ""})
        try:
            source = f.read_text(encoding="utf-8")
        except OSError:
            continue
        items.append({
            "name": stem,
            "label": meta["label"],
            "category": meta["category"],
            "description": meta["desc"],
            "source": source,
        })
    return items


@router.get("/opencode-tools")
async def list_opencode_tools():
    tools = _scan_tools()
    return {"success": True, "data": {"tools": tools, "install_path": ".opencode/tools/"}}


@router.get("/opencode-tools/{name}")
async def get_opencode_tool(name: str):
    filepath = TOOLS_DIR / f"{name}.ts"
    if not filepath.is_file():
        raise HTTPException(status_code=404, detail=f"Tool '{name}' not found")
    meta = KNOWN_TOOL_META.get(name, {"label": name, "category": "Other", "desc": ""})
    try:
        source = filepath.read_text(encoding="utf-8")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to read tool: {e}")
    return {
        "success": True,
        "data": {
            "name": name,
            "label": meta["label"],
            "category": meta["category"],
            "description": meta["desc"],
            "source": source,
        },
    }
