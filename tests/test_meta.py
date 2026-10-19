import sqlite3

import pytest

from opencode_cli_mcp import meta


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "meta.db"


def test_star_roundtrip(db_path):
    assert meta.get("s1", db_path=db_path)["starred"] is False
    meta.set_star("s1", True, db_path=db_path)
    assert meta.get("s1", db_path=db_path)["starred"] is True
    meta.set_star("s1", False, db_path=db_path)
    assert meta.get("s1", db_path=db_path)["starred"] is False
    # Idempotent
    meta.set_star("s1", False, db_path=db_path)
    assert meta.get("s1", db_path=db_path)["starred"] is False


def test_tags_normalised_and_deduped(db_path):
    meta.add_tags("s1", ["Neuro Biology", "neuro  biology", ""], db_path=db_path)
    assert meta.get("s1", db_path=db_path)["tags"] == ["neuro biology"]
    meta.add_tags("s1", ["Vienna"], db_path=db_path)
    assert meta.get("s1", db_path=db_path)["tags"] == ["neuro biology", "vienna"]


def test_remove_tags(db_path):
    meta.add_tags("s1", ["a", "b"], db_path=db_path)
    result = meta.remove_tags("s1", ["b", "missing"], db_path=db_path)
    assert result["tags"] == ["a"]


def test_get_many_bulk(db_path):
    meta.set_star("s1", True, db_path=db_path)
    meta.add_tags("s1", ["x"], db_path=db_path)
    meta.add_tags("s2", ["y"], db_path=db_path)
    out = meta.get_many(["s1", "s2", "s3"], db_path=db_path)
    assert out["s1"]["starred"] is True
    assert out["s1"]["tags"] == ["x"]
    assert out["s2"]["starred"] is False
    assert out["s2"]["tags"] == ["y"]
    assert out["s3"] == {"session_id": "s3", "starred": False, "note": "", "tags": []}
    assert meta.get_many([], db_path=db_path) == {}


def test_session_ids_filters(db_path):
    meta.set_star("s1", True, db_path=db_path)
    meta.set_star("s2", True, db_path=db_path)
    meta.add_tags("s2", ["neuro"], db_path=db_path)
    meta.add_tags("s3", ["neuro"], db_path=db_path)
    assert set(meta.session_ids(starred=True, db_path=db_path)) == {"s1", "s2"}
    assert set(meta.session_ids(tag="neuro", db_path=db_path)) == {"s2", "s3"}
    assert set(meta.session_ids(starred=True, tag="neuro", db_path=db_path)) == {"s2"}
    assert meta.session_ids(db_path=db_path) == []


def test_tag_counts_and_stats(db_path):
    meta.add_tags("s1", ["a", "b"], db_path=db_path)
    meta.add_tags("s2", ["a"], db_path=db_path)
    meta.set_star("s1", True, db_path=db_path)
    counts = meta.tags_with_counts(db_path=db_path)
    assert counts[0] == {"tag": "a", "count": 2}
    s = meta.stats(db_path=db_path)
    assert s["starred"] == 1
    assert s["tagged_sessions"] == 2
    assert s["distinct_tags"] == 2


def test_corrupt_db_surfaces_cleanly(tmp_path):
    bad = tmp_path / "meta.db"
    bad.write_text("not a database", encoding="utf-8")
    with pytest.raises(sqlite3.DatabaseError):
        meta.get("s1", db_path=bad)
