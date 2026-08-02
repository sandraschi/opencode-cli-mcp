"""REST surface for the opencode backup system (db + config, rotation, restore).

Wraps the MCP `opencode_backups` portmanteau for the webapp Backups page.
Mutating endpoints require confirmation flags; restore additionally refuses
while `opencode serve` is running unless force=true.
"""

from fastapi import APIRouter, HTTPException

from opencode_cli_mcp import backup

router = APIRouter(prefix="/backups", tags=["backups"])


def _err(e: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(e))


@router.get("/status")
async def backups_status():
    try:
        data = backup.status()
        data["last_autobackup"] = backup.last_autobackup()
        return {"success": True, "message": "Backup status", "data": data}
    except Exception as e:
        raise _err(e)


@router.get("/list")
async def backups_list(kind: str = "all"):
    try:
        entries = backup.list_backups(kind if kind != "all" else None)
        return {"success": True, "message": f"{len(entries)} backups", "data": {"backups": entries}}
    except Exception as e:
        raise _err(e)


@router.post("/create")
async def backups_create(kind: str = "all"):
    try:
        created = []
        if kind in ("db", "all"):
            created.append(backup.backup_db())
        if kind in ("config", "all"):
            created.append(backup.backup_config())
        return {"success": True, "message": f"Created {len(created)} backup(s)", "data": {"created": created}}
    except backup.BackupError as e:
        raise _err(e)


@router.post("/prune")
async def backups_prune(kind: str = "all"):
    try:
        result = backup.prune(kind if kind != "all" else None)
        return {"success": True, "message": f"Removed {len(result['removed'])} backup(s)", "data": result}
    except Exception as e:
        raise _err(e)


@router.post("/restore")
async def backups_restore(body: dict):
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="name required")
    if not body.get("confirm"):
        raise HTTPException(status_code=422, detail="confirm=true required - restore overwrites live data")
    try:
        await backup.ensure_restore_safe(force=bool(body.get("force")))
        is_db = name.startswith(backup._KIND_PREFIX["db"] + "-")
        result = backup.restore_db(name) if is_db else backup.restore_config(name)
        return {"success": True, "message": f"Restored {name}", "data": result}
    except backup.BackupError as e:
        raise _err(e)


@router.delete("/{name}")
async def backups_delete(name: str):
    try:
        result = backup.delete_backup(name)
        return {"success": True, "message": f"Deleted {name}", "data": result}
    except backup.BackupError as e:
        raise _err(e)
