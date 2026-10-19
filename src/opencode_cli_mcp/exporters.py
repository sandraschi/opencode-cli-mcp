"""Transcript exporters: markdown, html, docx, and the memops inbox hand-off.

Two jobs that are easy to confuse, kept in one module because both walk the
same transcript:

* ``export_transcript`` - write a readable file (md / html / docx) anywhere.
* ``send_to_memops`` - drop a frontmatter-tagged note into advanced-memory's
  zettelkasten inbox, where ``adn_inbox(operation="process")`` ingests it.

Both read ``opencode.db`` through :mod:`opencode_cli_mcp.depot` and never
write to it. docx conversion shells out to LibreOffice when present instead of
pulling a Python docx dependency into the runtime.
"""

import html
import os
import re
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from opencode_cli_mcp import depot

MEMOPS_INBOX_ENV = "MEMOPS_INBOX_DIR"
LIBREOFFICE_ENV = "LIBREOFFICE_BIN"

_DEFAULT_MEMOPS_INBOX = Path(r"D:\Dev\repos\advanced-memory-mcp\zettelkasten\inbox")

_SLUG_RE = re.compile(r"[^a-z0-9]+")


class ExportError(Exception):
    """Raised when an export cannot be produced (missing session, no engine)."""


def _slug(text: str, fallback: str = "session") -> str:
    slug = _SLUG_RE.sub("-", (text or "").lower()).strip("-")
    return (slug[:60] or fallback).strip("-")


def _fmt_ts(ts_ms: Any) -> str:
    try:
        ms = int(ts_ms)
    except (TypeError, ValueError):
        return ""
    try:
        return datetime.fromtimestamp(ms / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M UTC")
    except (OverflowError, OSError, ValueError):
        return ""


def _session_and_transcript(session_id: str, *, limit: int = 1000, db_path: Path | None = None):
    session = depot.get_session(session_id, db_path=db_path)
    if session is None:
        raise ExportError(f"session not found: {session_id}")
    transcript = depot.get_session_transcript(session_id, limit=limit, db_path=db_path)
    return session, transcript


def _meta_line(session: dict[str, Any]) -> str:
    parts = [
        str(session.get("time_created_display") or ""),
        f"agent: {session['agent']}" if session.get("agent") else "",
        f"project: {session.get('directory') or session.get('project_id') or ''}".rstrip(": "),
    ]
    return " · ".join(p for p in parts if p)


def to_markdown(
    session_id: str,
    *,
    db_path: Path | None = None,
    limit: int = 1000,
    frontmatter_tags: list[str] | None = None,
) -> str:
    """Session as markdown. Tags become YAML frontmatter (memops-friendly)."""
    session, transcript = _session_and_transcript(session_id, limit=limit, db_path=db_path)
    title = str(session.get("title") or session_id)
    tags = [t.strip().lower() for t in (frontmatter_tags or []) if t.strip()]
    head = [
        "---",
        f'title: "{title.replace(chr(34), chr(39))}"',
        f"session_id: {session_id}",
        f"agent: {session.get('agent') or 'opencode'}",
        f"created: {session.get('time_created_display') or ''}",
        f"tags: [{', '.join(tags)}]",
        "source: opencode",
        "---",
        "",
        f"# {title}",
        "",
        _meta_line(session),
        "",
    ]
    body: list[str] = []
    for msg in transcript:
        role = str(msg.get("role", "unknown"))
        stamp = _fmt_ts(msg.get("ts"))
        body.append(f"## {role} — {stamp}")
        body.append("")
        body.append(str(msg.get("text", "")).strip())
        body.append("")
    return "\n".join(head + body).rstrip() + "\n"


def to_html(session_id: str, *, db_path: Path | None = None, limit: int = 1000) -> str:
    """Standalone HTML page (dark theme, no external assets)."""
    session, transcript = _session_and_transcript(session_id, limit=limit, db_path=db_path)
    title = str(session.get("title") or session_id)
    rows = []
    for msg in transcript:
        role = html.escape(str(msg.get("role", "unknown")))
        text = html.escape(str(msg.get("text", "")))
        stamp = html.escape(_fmt_ts(msg.get("ts")))
        body = f"<pre>{text}</pre>" if "\n" in text else f"<p>{text}</p>"
        rows.append(f"<section class='msg {role}'><p class='ts'>{role} — {stamp}</p>{body}</section>")
    messages = "\n".join(rows) or "<p class='ts'>No text parts in this session.</p>"
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
body{{max-width:820px;margin:2em auto;padding:0 1em;font:14px/1.6 system-ui;color:#e2e8f0;background:#0f172a}}
h1{{color:#f59e0b;font-size:20px}} .meta{{color:#64748b;font-size:12px}}
.msg{{margin:1em 0;padding:1em;border-radius:8px;background:#1e293b}}
.msg.user{{border-left:3px solid #38bdf8}} .msg.assistant{{border-left:3px solid #f59e0b}}
.ts{{color:#64748b;font-size:12px;margin:0 0 .5em}}
pre{{background:#020617;padding:1em;border-radius:4px;overflow-x:auto;white-space:pre-wrap}}
</style></head><body>
<h1>{html.escape(title)}</h1><p class="meta">{html.escape(_meta_line(session))}</p>
{messages}
</body></html>"""


def find_libreoffice() -> Path | None:
    """Locate soffice(.exe): env override, PATH, then the usual install dirs."""
    env = os.environ.get(LIBREOFFICE_ENV)
    if env and Path(env).exists():
        return Path(env)
    found = shutil.which("soffice") or shutil.which("soffice.exe")
    if found:
        return Path(found)
    candidates = [
        Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
        Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
        Path("/usr/bin/soffice"),
        Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
    ]
    return next((p for p in candidates if p.exists()), None)


def to_docx(
    session_id: str,
    *,
    out_path: Path | None = None,
    db_path: Path | None = None,
    limit: int = 1000,
) -> dict[str, Any]:
    """Convert the session HTML to .docx with LibreOffice (headless).

    Returns ``{"path", "engine", "bytes"}``. Raises :class:`ExportError` when
    LibreOffice is not installed - never writes a fake/empty file.
    """
    soffice = find_libreoffice()
    if soffice is None:
        raise ExportError(
            "LibreOffice not found. Install it, or set LIBREOFFICE_BIN to soffice.exe. "
            "Markdown/HTML export works without it."
        )
    session, _ = _session_and_transcript(session_id, limit=limit, db_path=db_path)
    title = str(session.get("title") or session_id)
    target = out_path or (Path.home() / "Downloads" / f"opencode-{_slug(title)}-{session_id[:8]}.docx")
    target.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="oc-docx-") as tmp:
        src = Path(tmp) / "session.html"
        src.write_text(to_html(session_id, db_path=db_path, limit=limit), encoding="utf-8")
        proc = subprocess.run(  # noqa: S603 - fixed binary, temp paths we created
            [
                str(soffice),
                "--headless",
                "--norestore",
                # Filter name is required: bare "docx" aborts with
                # "no export filter for ...docx" on this LibreOffice build.
                "--convert-to",
                "docx:Office Open XML Text",
                "--outdir",
                tmp,
                str(src),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        produced = Path(tmp) / "session.docx"
        if proc.returncode != 0 or not produced.exists():
            raise ExportError(f"LibreOffice conversion failed: {(proc.stderr or proc.stdout).strip()[:400]}")
        shutil.move(str(produced), target)
    return {"path": str(target), "engine": str(soffice), "bytes": target.stat().st_size}


def export_transcript(
    session_id: str,
    fmt: str = "md",
    *,
    out_path: Path | None = None,
    db_path: Path | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Write md/html/docx. md/html go to ``out_path`` or ~/Downloads."""
    fmt = (fmt or "md").lower()
    if fmt not in ("md", "markdown", "html", "docx"):
        raise ExportError(f"unsupported format '{fmt}' (md, html, docx)")
    if fmt in ("md", "markdown"):
        session, _ = _session_and_transcript(session_id, db_path=db_path)
        target = out_path or (
            Path.home() / "Downloads" / f"opencode-{_slug(str(session.get('title') or session_id))}-{session_id[:8]}.md"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(to_markdown(session_id, db_path=db_path, frontmatter_tags=tags), encoding="utf-8")
        return {"path": str(target), "format": "md", "bytes": target.stat().st_size}
    if fmt == "html":
        session, _ = _session_and_transcript(session_id, db_path=db_path)
        target = out_path or (
            Path.home()
            / "Downloads"
            / f"opencode-{_slug(str(session.get('title') or session_id))}-{session_id[:8]}.html"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(to_html(session_id, db_path=db_path), encoding="utf-8")
        return {"path": str(target), "format": "html", "bytes": target.stat().st_size}
    return {"format": "docx", **to_docx(session_id, out_path=out_path, db_path=db_path)}


def memops_inbox_dir() -> Path:
    env = os.environ.get(MEMOPS_INBOX_ENV)
    return Path(env) if env else _DEFAULT_MEMOPS_INBOX


def send_to_memops(
    session_id: str,
    *,
    tags: list[str] | None = None,
    inbox_dir: Path | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Drop a frontmatter note into memops' inbox (durable file hand-off).

    File drop beats an HTTP call here: the inbox processor already owns
    conversion, dedupe and folder placement, and a note that lands on disk
    survives a memops restart. Run ``adn_inbox(operation="process")`` (or let
    the watcher) to ingest.
    """
    inbox = inbox_dir or memops_inbox_dir()
    if not inbox.exists():
        raise ExportError(
            f"memops inbox not found: {inbox}. Set {MEMOPS_INBOX_ENV} to the zettelkasten/inbox directory."
        )
    session, _ = _session_and_transcript(session_id, db_path=db_path)
    title = str(session.get("title") or session_id)
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    target = inbox / f"opencode-{stamp}-{_slug(title)}-{session_id[:8]}.md"
    target.write_text(to_markdown(session_id, db_path=db_path, frontmatter_tags=tags), encoding="utf-8")
    return {
        "path": str(target),
        "inbox": str(inbox),
        "bytes": target.stat().st_size,
        "next_step": 'Run adn_inbox(operation="process") (or wait for the inbox watcher) to ingest it.',
    }
