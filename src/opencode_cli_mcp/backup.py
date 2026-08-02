"""opencode database + config backup with rotation and disk-space guard.

Safeguard for the opencode SQLite depot (~/.local/share/opencode/opencode.db)
and the opencode config directory (~/.config/opencode). opencode has no
built-in backup; a corrupted or rolled-back database (bad plugin, failed
experiment, disk issue) would otherwise lose every session and transcript.

Design:
- DB snapshots use SQLite's online backup API (consistent even while the
  opencode server holds the file in WAL mode - no stop required).
- Config backups are ZIP archives of ~/.config/opencode (node_modules and
  caches excluded; note the archive contains credentials like auth.json -
  keep it local).
- Rotation: newest-N kept per kind (default 10), oldest deleted by filename.
- Storage guard: creation is skipped when the backup volume has less than
  MIN_FREE_MB free (default 500 MB) or the source is larger than 50% of free.
- Restore refuses while `opencode serve` is running (unless force=True):
  the live server would resurrect rows / hold the file.

Env:
    OPENCODE_CLI_MCP_BACKUP_DIR      backup directory (default ~/.local/share/opencode-cli-mcp/backups)
    OPENCODE_CLI_MCP_BACKUP_RETENTION   backups kept per kind (default 10)
    OPENCODE_CLI_MCP_BACKUP_MIN_FREE_MB  min free bytes on the volume (default 500)
    OPENCODE_CLI_MCP_BACKUP_INTERVAL_HOURS  autobackup cadence, 0 = off (default 24)
"""

import logging
import os
import shutil
import sqlite3
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from opencode_cli_mcp.depot import default_db_path

logger = logging.getLogger(__name__)

_KIND_PREFIX = {"db": "opencode-db", "config": "opencode-config"}


class BackupError(Exception):
    """Raised when a backup/restore operation cannot proceed."""


def backup_dir() -> Path:
    path = Path(
        os.environ.get("OPENCODE_CLI_MCP_BACKUP_DIR", Path.home() / ".local" / "share" / "opencode-cli-mcp" / "backups")
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


def retention() -> int:
    try:
        return max(1, int(os.environ.get("OPENCODE_CLI_MCP_BACKUP_RETENTION", "10")))
    except ValueError:
        return 10


def min_free_bytes() -> int:
    try:
        return max(0, int(os.environ.get("OPENCODE_CLI_MCP_BACKUP_MIN_FREE_MB", "500"))) * 1024 * 1024
    except ValueError:
        return 500 * 1024 * 1024


def autobackup_interval_hours() -> int:
    try:
        return max(0, int(os.environ.get("OPENCODE_CLI_MCP_BACKUP_INTERVAL_HOURS", "24")))
    except ValueError:
        return 24


def config_dir() -> Path:
    env = os.environ.get("OPENCODE_CONFIG")
    if env:
        return Path(env)
    return Path.home() / ".config" / "opencode"


def _timestamp() -> str:
    # Microsecond resolution: rapid consecutive backups must not collide
    # (second-resolution names would overwrite each other).
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")


_TS_FORMATS = ("%Y%m%d-%H%M%S-%f", "%Y%m%d-%H%M%S")


def _parse_created(stem: str) -> str | None:
    for fmt in _TS_FORMATS:
        try:
            return datetime.strptime(stem, fmt).replace(tzinfo=UTC).isoformat()
        except ValueError:
            continue
    return None


def _check_storage(source_size: int) -> None:
    """Abort when the backup volume cannot safely hold another copy."""
    free = shutil.disk_usage(backup_dir()).free
    if free < min_free_bytes():
        raise BackupError(
            f"insufficient disk space: {free / 1024 / 1024:.0f} MB free "
            f"(min {min_free_bytes() / 1024 / 1024:.0f} MB) - backup skipped"
        )
    if source_size > free // 2:
        raise BackupError(
            f"backup source ({source_size / 1024 / 1024:.0f} MB) exceeds half of free "
            f"space ({free / 1024 / 1024:.0f} MB) - backup skipped"
        )


def _rotate(kind: str) -> list[str]:
    """Delete oldest backups beyond the retention window. Returns removed names."""
    keep = retention()
    files = sorted(_kind_files(kind), key=lambda p: p.name, reverse=True)
    removed = []
    for old in files[keep:]:
        try:
            old.unlink()
            removed.append(old.name)
        except OSError as e:
            logger.warning("backup rotation: could not delete %s: %s", old, e)
    if removed:
        logger.info("backup rotation: removed %s (retention %d)", removed, keep)
    return removed


def _kind_files(kind: str) -> list[Path]:
    prefix = _KIND_PREFIX[kind]
    return [p for p in backup_dir().glob(f"{prefix}-*") if p.is_file()]


def backup_db() -> dict[str, Any]:
    """Consistent snapshot of opencode.db via the SQLite online backup API."""
    src_path = Path(default_db_path())
    if not src_path.is_file():
        raise BackupError(f"opencode database not found at {src_path}")

    _check_storage(src_path.stat().st_size)

    dest = backup_dir() / f"{_KIND_PREFIX['db']}-{_timestamp()}.sqlite3"
    try:
        src = sqlite3.connect(f"file:{src_path.as_posix()}?mode=ro", uri=True)
        try:
            dst = sqlite3.connect(dest)
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
    except sqlite3.Error as e:
        raise BackupError(f"database backup failed: {e}") from e

    _rotate("db")
    size = dest.stat().st_size
    logger.info("backed up opencode.db -> %s (%d bytes)", dest.name, size)
    return {"kind": "db", "name": dest.name, "path": str(dest), "size": size}


def backup_config() -> dict[str, Any]:
    """ZIP the opencode config directory (node_modules/caches excluded)."""
    src_dir = config_dir()
    if not src_dir.is_dir():
        raise BackupError(f"opencode config directory not found at {src_dir}")

    _check_storage(1)  # config archives are small; guard is about free space

    dest = backup_dir() / f"{_KIND_PREFIX['config']}-{_timestamp()}.zip"
    try:
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in sorted(src_dir.rglob("*")):
                if p.is_file() and not _config_excluded(p):
                    zf.write(p, p.relative_to(src_dir))
    except OSError as e:
        raise BackupError(f"config backup failed: {e}") from e

    _rotate("config")
    size = dest.stat().st_size
    logger.info("backed up opencode config -> %s (%d bytes)", dest.name, size)
    return {"kind": "config", "name": dest.name, "path": str(dest), "size": size}


def _config_excluded(p: Path) -> bool:
    parts = p.parts
    return any(
        part in ("node_modules", ".cache", "__pycache__", "logs", "target")
        or p.suffix == ".tsbuildinfo"
        or p.name.endswith(".log")
        for part in parts
    )


def list_backups(kind: str | None = None) -> list[dict[str, Any]]:
    kinds = ["db", "config"] if kind is None else [kind]
    entries = []
    for k in kinds:
        for p in _kind_files(k):
            created = _parse_created(p.stem)
            entries.append(
                {
                    "kind": k,
                    "name": p.name,
                    "path": str(p),
                    "size": p.stat().st_size,
                    "created": created,
                }
            )
    entries.sort(key=lambda e: e["created"] or "", reverse=True)
    return entries


def prune(kind: str | None = None) -> dict[str, Any]:
    """Delete all but the newest retention() backups of each kind."""
    kinds = ["db", "config"] if kind is None else [kind]
    removed = []
    for k in kinds:
        removed.extend(_rotate(k))
    return {"removed": removed, "remaining": list_backups(kind)}


def _find_backup(name: str, kind: str) -> Path:
    prefix = _KIND_PREFIX[kind]
    if not name.startswith(prefix + "-"):
        raise BackupError(f"'{name}' is not a {kind} backup")
    path = backup_dir() / name
    if not path.is_file():
        raise BackupError(f"backup not found: {name}")
    return path


async def _serve_running() -> bool:
    """True when an opencode serve API answers on the default port (no spawn)."""
    from opencode_cli_mcp.client import get_client

    try:
        return await get_client()._ping()
    except Exception:
        return False


async def ensure_restore_safe(force: bool) -> None:
    """Raise BackupError when restoring a DB while opencode serve is live."""
    if force:
        return
    if await _serve_running():
        raise BackupError(
            "opencode serve is running - stop it before restoring (or pass force=True "
            "to override; the running server may then resurrect rows)"
        )


def restore_db(name: str) -> dict[str, Any]:
    """Restore a db backup over opencode.db. Call ensure_restore_safe() first."""
    src = _find_backup(name, "db")
    _validate_sqlite(src)

    db_path = Path(default_db_path())
    if not db_path.is_file():
        raise BackupError(f"opencode database not found at {db_path}")

    # Safety net: keep the current (possibly bad) DB before overwriting.
    safeguard = backup_dir() / f"opencode-db-pre-restore-{_timestamp()}.sqlite3"
    shutil.copy2(db_path, safeguard)
    logger.info("pre-restore safeguard: %s", safeguard.name)

    shutil.copy2(src, db_path)
    # Stale WAL/SHM from the old database must not leak into the restored one.
    for suffix in ("-wal", "-shm"):
        stale = Path(f"{db_path}{suffix}")
        if stale.exists():
            stale.unlink()
    logger.info("restored %s -> %s", src.name, db_path)
    return {"restored": name, "safeguard": safeguard.name, "database": str(db_path)}


def restore_config(name: str) -> dict[str, Any]:
    """Restore a config zip over ~/.config/opencode (current config zipped first)."""
    src = _find_backup(name, "config")
    target = config_dir()
    if not target.is_dir():
        raise BackupError(f"config directory not found at {target}")

    safeguard = backup_dir() / f"opencode-config-pre-restore-{_timestamp()}.zip"
    with zipfile.ZipFile(safeguard, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(target.rglob("*")):
            if p.is_file() and not _config_excluded(p):
                zf.write(p, p.relative_to(target))
    logger.info("pre-restore safeguard: %s", safeguard.name)

    with zipfile.ZipFile(src) as zf:
        zf.extractall(target)
    logger.info("restored %s -> %s", src.name, target)
    return {"restored": name, "safeguard": safeguard.name, "config_dir": str(target)}


def delete_backup(name: str) -> dict[str, Any]:
    kind = "db" if name.startswith(_KIND_PREFIX["db"] + "-") else "config"
    path = _find_backup(name, kind)
    path.unlink()
    return {"deleted": name}


def _validate_sqlite(path: Path) -> None:
    try:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        try:
            row = conn.execute("PRAGMA integrity_check").fetchone()
        finally:
            conn.close()
    except sqlite3.Error as e:
        raise BackupError(f"backup is not a valid SQLite database: {e}") from e
    if not row or row[0] != "ok":
        raise BackupError(f"backup failed SQLite integrity check: {row}")


async def await_client_ok(client) -> bool:
    """Best-effort liveness probe of the opencode serve API."""
    try:
        return await client._ping()
    except Exception:
        return False


def status() -> dict[str, Any]:
    db_path = Path(default_db_path())
    cfg_dir = config_dir()
    bdir = backup_dir()
    try:
        free = shutil.disk_usage(bdir).free
    except OSError:
        free = 0
    backups = list_backups()
    return {
        "db_path": str(db_path),
        "db_exists": db_path.is_file(),
        "db_size": db_path.stat().st_size if db_path.is_file() else 0,
        "config_dir": str(cfg_dir),
        "config_exists": cfg_dir.is_dir(),
        "backup_dir": str(bdir),
        "free_bytes": free,
        "min_free_bytes": min_free_bytes(),
        "retention": retention(),
        "autobackup_interval_hours": autobackup_interval_hours(),
        "counts": {
            "db": sum(1 for b in backups if b["kind"] == "db"),
            "config": sum(1 for b in backups if b["kind"] == "config"),
        },
        "last_backup": backups[0] if backups else None,
    }


# --- autobackup ------------------------------------------------------------

_last_autobackup: dict[str, Any] | None = None


def last_autobackup() -> dict[str, Any] | None:
    return _last_autobackup


def set_last_autobackup(report: dict[str, Any] | None) -> None:
    global _last_autobackup
    _last_autobackup = report


def run_autobackup() -> dict[str, Any]:
    """Create db + config backups, tolerating per-kind failure. Returns a report."""
    results: list[dict[str, Any]] = []
    for kind, fn in (("db", backup_db), ("config", backup_config)):
        try:
            results.append({"kind": kind, "ok": True, **fn()})
        except BackupError as e:
            logger.warning("autobackup %s skipped: %s", kind, e)
            results.append({"kind": kind, "ok": False, "error": str(e)})
    return {"timestamp": datetime.now(UTC).isoformat(), "results": results}
