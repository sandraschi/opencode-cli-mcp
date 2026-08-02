"""Backup system tests: snapshot, rotation, disk guard, restore round-trip, config zip."""

import sqlite3
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from opencode_cli_mcp import backup


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENCODE_CLI_MCP_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("OPENCODE_CLI_MCP_BACKUP_RETENTION", "2")
    monkeypatch.setenv("OPENCODE_CLI_MCP_BACKUP_MIN_FREE_MB", "500")
    return tmp_path


def _make_db(path: Path, marker: str = "hello") -> Path:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    conn.execute("INSERT INTO t (v) VALUES (?)", (marker,))
    conn.commit()
    conn.close()
    return path


def test_backup_db_snapshot(env, tmp_path, monkeypatch):
    db = tmp_path / "opencode.db"
    _make_db(db)
    monkeypatch.setattr(backup, "default_db_path", lambda: db)
    monkeypatch.setattr(backup, "config_dir", lambda: tmp_path / "nope")

    result = backup.backup_db()
    assert result["kind"] == "db"
    dest = Path(result["path"])
    assert dest.is_file() and dest.stat().st_size > 0
    # snapshot is a readable sqlite db with the same content
    conn = sqlite3.connect(dest)
    assert conn.execute("SELECT v FROM t").fetchone()[0] == "hello"
    conn.close()


def test_backup_db_rotation(env, tmp_path, monkeypatch):
    db = tmp_path / "opencode.db"
    _make_db(db)
    monkeypatch.setattr(backup, "default_db_path", lambda: db)

    for _ in range(4):  # retention=2 -> 2 remain
        backup.backup_db()

    entries = backup.list_backups("db")
    assert len(entries) == 2


def test_backup_db_disk_guard(env, tmp_path, monkeypatch):
    db = tmp_path / "opencode.db"
    _make_db(db)
    monkeypatch.setattr(backup, "default_db_path", lambda: db)

    from types import SimpleNamespace

    with patch.object(backup.shutil, "disk_usage", return_value=SimpleNamespace(free=1)):
        with pytest.raises(backup.BackupError, match="insufficient disk space"):
            backup.backup_db()
    assert backup.list_backups("db") == []


def test_backup_missing_db(env, tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "default_db_path", lambda: tmp_path / "missing.db")
    with pytest.raises(backup.BackupError, match="not found"):
        backup.backup_db()


def test_restore_db_round_trip(env, tmp_path, monkeypatch):
    db = tmp_path / "opencode.db"
    _make_db(db, "before")
    monkeypatch.setattr(backup, "default_db_path", lambda: db)

    snap = backup.backup_db()

    # corrupt the live db
    conn = sqlite3.connect(db)
    conn.execute("DROP TABLE t")
    conn.commit()
    conn.close()

    result = backup.restore_db(snap["name"])
    assert "pre-restore" in result["safeguard"]
    conn = sqlite3.connect(db)
    assert conn.execute("SELECT v FROM t").fetchone()[0] == "before"
    conn.close()
    # safeguard of the corrupted db exists
    assert (Path(env) / "backups" / result["safeguard"]).is_file()


def test_restore_invalid_backup(env, tmp_path, monkeypatch):
    bogus = env / "backups" / "opencode-db-20260101-000000.sqlite3"
    bogus.parent.mkdir(parents=True, exist_ok=True)
    bogus.write_text("not a database")
    with pytest.raises(backup.BackupError, match="not a valid SQLite"):
        backup.restore_db(bogus.name)


def test_backup_config_zip(env, tmp_path, monkeypatch):
    cfg = tmp_path / "config"
    (cfg / "sub").mkdir(parents=True)
    (cfg / "opencode.json").write_text('{"x": 1}')
    (cfg / "secret.txt").write_text("s")
    (cfg / "node_modules").mkdir()
    (cfg / "node_modules" / "big.js").write_text("x" * 1000)
    monkeypatch.setattr(backup, "config_dir", lambda: cfg)

    result = backup.backup_config()
    with zipfile.ZipFile(result["path"]) as zf:
        names = zf.namelist()
    assert "opencode.json" in names
    assert "secret.txt" in names
    assert not any("node_modules" in n for n in names)


def test_list_prune_delete(env, tmp_path, monkeypatch):
    db = tmp_path / "opencode.db"
    _make_db(db)
    monkeypatch.setattr(backup, "default_db_path", lambda: db)
    monkeypatch.setattr(backup, "config_dir", lambda: tmp_path / "nope")

    backup.backup_db()
    backup.backup_db()
    assert len(backup.list_backups()) == 2

    pruned = backup.prune("db")
    assert len(pruned["removed"]) == 0  # retention 2 keeps both

    names = [b["name"] for b in backup.list_backups("db")]
    deleted = backup.delete_backup(names[0])
    assert deleted["deleted"] == names[0]
    assert len(backup.list_backups("db")) == 1


def test_status_shape(env, tmp_path, monkeypatch):
    db = tmp_path / "opencode.db"
    _make_db(db)
    monkeypatch.setattr(backup, "default_db_path", lambda: db)
    monkeypatch.setattr(backup, "config_dir", lambda: tmp_path / "config")

    st = backup.status()
    for key in ("db_path", "backup_dir", "free_bytes", "min_free_bytes", "retention", "counts"):
        assert key in st
    assert st["retention"] == 2
    assert st["counts"]["db"] == 0


def test_run_autobackup_tolerates_missing_kind(env, tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "default_db_path", lambda: tmp_path / "missing.db")
    monkeypatch.setattr(backup, "config_dir", lambda: tmp_path / "nope")
    report = backup.run_autobackup()
    assert all(r["ok"] is False for r in report["results"])
