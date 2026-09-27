from fastapi import APIRouter

from api.routes.opencode_tools import _scan_tools

router = APIRouter(tags=["skills"])


@router.get("/skills")
async def list_skills():
    """Canonical skill listing (fleet-standard path for skill-first Chat).

    This server's agent-facing skills are its OpenCode custom tools
    (``.opencode/tools/*.ts``) - the same live inventory as
    ``GET /api/opencode-tools``, projected to the fleet skill shape
    (no invented URIs; ``install_path`` points at the real files).
    """
    tools = _scan_tools()
    skills = [
        {
            "name": t["name"],
            "label": t["label"],
            "category": t["category"],
            "description": t["description"],
        }
        for t in tools
    ]
    return {
        "success": True,
        "message": f"{len(skills)} skills",
        "data": {"skills": skills, "install_path": ".opencode/tools/"},
    }
