"""opencode_backups portmanteau - database/config backup, rotation, restore.

Safeguard for the opencode SQLite depot + config directory: consistent online
snapshots (SQLite backup API, works while opencode runs), rotation, disk-space
guard, and guarded restore (refuses while `opencode serve` is live unless
force=True).
"""

from typing import Annotated, Literal

from pydantic import Field

from opencode_cli_mcp import backup


def _missing(action: str, param: str) -> dict:
    return {
        "success": False,
        "message": f"action '{action}' requires '{param}'",
        "data": {},
        "recovery_options": [f"Call again with {param} set."],
    }


def _wrap(action: str, ok: bool, message: str, data: dict) -> dict:
    return {"success": ok, "message": message, "data": data}


async def opencode_backups(
    action: Annotated[
        Literal["status", "create", "list", "prune", "restore", "delete"],
        Field(
            description=(
                "status: paths, free space, counts, last backup. create: take a snapshot "
                "of the database (kind=db), config (kind=config), or both (kind=all). "
                "list: backups with sizes/dates. prune: drop old backups beyond retention. "
                "restore: overwrite the database or config from a backup (confirm=True; "
                "refuses while opencode serve is running unless force=True). "
                "delete: remove one backup file."
            )
        ),
    ],
    kind: Annotated[
        Literal["db", "config", "all"],
        Field(description="Target: database, config directory, or both (create/prune)"),
    ] = "all",
    name: Annotated[str | None, Field(description="Backup filename (required for restore/delete)")] = None,
    confirm: Annotated[bool, Field(description="Must be True for restore (overwrites live data)")] = False,
    force: Annotated[bool, Field(description="Allow restore while opencode serve is running")] = False,
) -> dict:
    """Backup the opencode database and config with rotation + disk guard; restore when needed.

    ## Return Format
    {"success": bool, "message": str, "data": dict}

    ## Examples
    opencode_backups(action="status")
    opencode_backups(action="create", kind="all")
    opencode_backups(action="list", kind="db")
    opencode_backups(action="restore", name="opencode-db-20260802-120000.sqlite3", confirm=True)
    """

    try:
        if action == "status":
            return _wrap(action, True, "Backup status", backup.status())

        if action == "list":
            entries = backup.list_backups(kind if kind != "all" else None)
            return _wrap(action, True, f"Found {len(entries)} backups", {"backups": entries})

        if action == "create":
            results = []
            if kind in ("db", "all"):
                results.append(backup.backup_db())
            if kind in ("config", "all"):
                results.append(backup.backup_config())
            return _wrap(action, True, f"Created {len(results)} backup(s)", {"created": results})

        if action == "prune":
            result = backup.prune(kind if kind != "all" else None)
            return _wrap(action, True, f"Removed {len(result['removed'])} backup(s)", result)

        if action == "delete":
            if not name:
                return _missing(action, "name")
            return _wrap(action, True, f"Deleted {name}", backup.delete_backup(name))

        if action == "restore":
            if not name:
                return _missing(action, "name")
            if not confirm:
                return {
                    "success": False,
                    "message": "confirm=True required - restore overwrites live data",
                    "data": {},
                    "recovery_options": ["Call again with confirm=True"],
                }
            await backup.ensure_restore_safe(force)
            is_db = name.startswith(backup._KIND_PREFIX["db"] + "-")
            result = backup.restore_db(name) if is_db else backup.restore_config(name)
            return _wrap(action, True, f"Restored {name}", result)

        return _missing(action, "action")  # pragma: no cover - Literal bounds it
    except backup.BackupError as e:
        return _wrap(action, False, str(e), {"action": action})
    except Exception as e:  # pragma: no cover - defensive boundary
        return _wrap(action, False, f"Backup error: {e}", {"action": action})
