import pytest

from opencode_cli_mcp import exporters
from tests.test_depot import depot_db  # noqa: F401 - pytest fixture re-export


@pytest.fixture()
def session_db(depot_db):  # noqa: F811 - fixture consumed
    return depot_db


def test_to_markdown_has_frontmatter_and_transcript(session_db):
    md = exporters.to_markdown("sess_active", db_path=session_db, frontmatter_tags=["Neuro Biology", "vienna"])
    assert md.startswith("---\n")
    assert "session_id: sess_active" in md
    assert "tags: [neuro biology, vienna]" in md
    assert "source: opencode" in md
    assert "## user" in md or "## assistant" in md
    assert "4090" in md


def test_to_html_standalone(session_db):
    page = exporters.to_html("sess_active", db_path=session_db)
    assert page.startswith("<!DOCTYPE html>")
    assert "<section class='msg" in page
    assert "4090" in page


def test_export_markdown_file(session_db, tmp_path):
    out = tmp_path / "chat.md"
    result = exporters.export_transcript("sess_active", "md", out_path=out, db_path=session_db)
    assert result["format"] == "md"
    assert out.exists() and out.stat().st_size > 100
    assert "session_id: sess_active" in out.read_text(encoding="utf-8")


def test_export_html_file(session_db, tmp_path):
    out = tmp_path / "chat.html"
    result = exporters.export_transcript("sess_active", "html", out_path=out, db_path=session_db)
    assert result["format"] == "html"
    assert "<!DOCTYPE html>" in out.read_text(encoding="utf-8")


def test_export_rejects_bad_format(session_db):
    with pytest.raises(exporters.ExportError):
        exporters.export_transcript("sess_active", "pdf", db_path=session_db)


def test_export_unknown_session(session_db, tmp_path):
    with pytest.raises(exporters.ExportError):
        exporters.export_transcript("nope", "md", out_path=tmp_path / "x.md", db_path=session_db)


def test_send_to_memops_writes_note(session_db, tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    result = exporters.send_to_memops("sess_active", tags=["neuro"], inbox_dir=inbox, db_path=session_db)
    note = inbox / result["path"].split("\\")[-1] if "\\" in result["path"] else inbox / result["path"].split("/")[-1]
    assert note.exists()
    text = note.read_text(encoding="utf-8")
    assert "tags: [neuro]" in text
    assert "source: opencode" in text
    assert "adn_inbox" in result["next_step"]


def test_send_to_memops_missing_inbox(session_db, tmp_path):
    with pytest.raises(exporters.ExportError):
        exporters.send_to_memops("sess_active", inbox_dir=tmp_path / "absent", db_path=session_db)


def test_docx_without_libreoffice(session_db, tmp_path, monkeypatch):
    monkeypatch.setattr(exporters, "find_libreoffice", lambda: None)
    with pytest.raises(exporters.ExportError, match="LibreOffice not found"):
        exporters.export_transcript("sess_active", "docx", out_path=tmp_path / "x.docx", db_path=session_db)


@pytest.mark.skipif(exporters.find_libreoffice() is None, reason="LibreOffice not installed")
def test_docx_real_conversion(session_db, tmp_path):
    out = tmp_path / "chat.docx"
    result = exporters.export_transcript("sess_active", "docx", out_path=out, db_path=session_db)
    assert out.exists()
    assert out.stat().st_size > 1000
    assert result["bytes"] == out.stat().st_size
