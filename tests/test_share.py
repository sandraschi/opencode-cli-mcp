"""Tests for unlisted share pages (opencode_cli_mcp.share).

Builds a throwaway opencode.db (same shape as tests/test_depot.py) and a
throwaway shares dir. Never touches the real depot or real shares.
"""

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from opencode_cli_mcp import share as sh
from tests.test_depot import SCHEMA


@pytest.fixture()
def share_env(tmp_path: Path):
    db_path = tmp_path / "opencode.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    now = int(datetime.now(UTC).timestamp() * 1000)
    conn.execute(
        "INSERT INTO session (id, project_id, slug, directory, title, version, time_created, time_updated) "
        "VALUES (?,?,?,?,?,?,?,?)",
        ("sess_01", "proj_a", "s1", r"D:\Dev\repos\demo", "Demo <session>", "1.0.0", now - 3600000, now),
    )
    conn.execute(
        "INSERT INTO message (id, session_id, time_created, time_updated, data) VALUES (?,?,?,?,?)",
        ("msg1", "sess_01", now, now, json.dumps({"role": "user", "time": {"created": now}})),
    )
    conn.execute(
        "INSERT INTO message (id, session_id, time_created, time_updated, data) VALUES (?,?,?,?,?)",
        ("msg2", "sess_01", now, now, json.dumps({"role": "assistant", "time": {"created": now}})),
    )
    conn.execute(
        "INSERT INTO part (id, message_id, session_id, time_created, time_updated, data) VALUES (?,?,?,?,?,?)",
        ("part1", "msg1", "sess_01", now, now, json.dumps({"type": "text", "text": "What did we decide?"})),
    )
    conn.execute(
        "INSERT INTO part (id, message_id, session_id, time_created, time_updated, data) VALUES (?,?,?,?,?,?)",
        (
            "part2",
            "msg2",
            "sess_01",
            now,
            now,
            json.dumps({"type": "text", "text": "Line one\nLine two <b>bold</b>"}),
        ),
    )
    conn.commit()
    conn.close()
    base = tmp_path / "shares"
    os.environ["OPENCODE_DB_PATH"] = str(db_path)
    yield base
    os.environ.pop("OPENCODE_DB_PATH", None)


def test_create_share_roundtrip(share_env: Path):
    data = sh.create_share("sess_01", base=share_env)
    assert data["url_path"] == f"/share/{data['token']}"
    assert data["title"] == "Demo <session>"
    assert data["messages"] == 2
    page = share_env / f"{data['token']}.html"
    assert page.exists()
    body = page.read_text(encoding="utf-8")
    assert "Demo &lt;session&gt;" in body  # title escaped
    assert "Line two &lt;b&gt;bold&lt;/b&gt;" in body  # part text escaped
    assert "<pre>" in body  # multiline part uses pre
    assert 'name="robots" content="noindex' in body


def test_create_share_missing_session(share_env: Path):
    with pytest.raises(sh.ShareError):
        sh.create_share("nope", base=share_env)


def test_page_path_validation(share_env: Path):
    data = sh.create_share("sess_01", base=share_env)
    assert sh.share_page_path(data["token"], base=share_env) is not None
    assert sh.share_page_path("nosuchtoken12345", base=share_env) is None
    assert sh.share_page_path("../evil", base=share_env) is None
    assert sh.share_page_path("", base=share_env) is None


def test_unshare_flows(share_env: Path):
    first = sh.create_share("sess_01", base=share_env)
    second = sh.create_share("sess_01", base=share_env)
    assert sh.session_share("sess_01", base=share_env)["token"] in (first["token"], second["token"])
    assert len(sh.list_shares(base=share_env)) == 2
    assert sh.unshare_token(first["token"], base=share_env) is True
    assert sh.unshare_token(first["token"], base=share_env) is False
    assert sh.session_share("sess_01", base=share_env)["token"] == second["token"]
    assert sh.unshare_session("sess_01", base=share_env) == 1
    assert sh.list_shares(base=share_env) == []
    assert sh.session_share("sess_01", base=share_env) is None
    assert not (share_env / f"{second['token']}.html").exists()
