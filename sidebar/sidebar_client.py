"""Thin TSV CLI over opencode_cli_mcp.depot for the AHK sidebar companion.

Commands (stdout is TSV or single-line ok/err, exit 0/1):
  list [search]        active sessions, newest first
  preview SID [limit]  wrapped YOU/AI tail lines joined with ' // '
  rename SID TITLE
  archive SID | unarchive SID
  delete SID yes       (double-gated: caller confirms AND literal 'yes' here)
"""

import json
import sys
import textwrap
from datetime import datetime

from opencode_cli_mcp import depot as d


def _short_model(m) -> str:
    try:
        mj = json.loads(m) if isinstance(m, str) else (m or {})
        mid = mj.get("id", "")
        prov = mj.get("providerID", "")
        return ((prov + "/" + mid) if prov else mid)[:30]
    except Exception:
        return str(m or "")[:30]


def _short_ts(ms) -> str:
    try:
        return datetime.fromtimestamp(int(ms) / 1000).strftime("%m-%d %H:%M")
    except Exception:
        return ""


def cmd_list(search: str):
    data = d.list_sessions(status="active", search=search or None, limit=100, sort="updated")
    for s in data["sessions"]:
        cost = s.get("cost_est")
        if cost is None:
            cost = s.get("cost") or 0
        try:
            cost_s = f"{float(cost):.2f}"
        except Exception:
            cost_s = "0.00"
        print(
            "\t".join(
                [
                    str(s.get("id", "")),
                    str(s.get("title", "")),
                    str(s.get("directory", "")),
                    _short_ts(s.get("time_updated")),
                    _short_model(s.get("model")),
                    cost_s,
                ]
            )
        )


def cmd_preview(sid: str, limit: int):
    parts = d.get_session_transcript(sid, limit=400)
    lines = []
    for p in parts[-60:]:
        txt = (p.get("text") or "").strip().replace("\n", " ")
        if not txt:
            continue
        who = "YOU" if p.get("role") == "user" else "AI"
        lines.append(who + ": " + txt[:220])
    tail = lines[-12:]
    wrapped = []
    for ln in tail:
        wrapped.extend(textwrap.wrap(ln, width=88)[:3])
        if len(wrapped) >= 14:
            break
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(sid + "\t" + " // ".join(wrapped[:14])[:1500])


def cmd_previews():
    data = d.list_sessions(status="active", limit=100, sort="updated")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for s in data["sessions"]:
        sid = s.get("id", "")
        parts = d.get_session_transcript(sid, limit=400)
        lines = []
        for p in parts[-60:]:
            txt = (p.get("text") or "").strip().replace("\n", " ")
            if not txt:
                continue
            who = "YOU" if p.get("role") == "user" else "AI"
            lines.append(who + ": " + txt[:220])
        tail = lines[-12:]
        wrapped = []
        for ln in tail:
            wrapped.extend(textwrap.wrap(ln, width=88)[:3])
            if len(wrapped) >= 14:
                break
        print(sid + "\t" + " // ".join(wrapped[:14])[:1500])


def main(argv) -> int:
    if not argv:
        print("err usage: list|preview|previews|rename|archive|unarchive|delete", file=sys.stderr)
        return 1
    try:
        if argv[0] == "list":
            cmd_list(argv[1] if len(argv) > 1 else "")
        elif argv[0] == "previews":
            cmd_previews()
        elif argv[0] == "preview" and len(argv) > 1:
            cmd_preview(argv[1], int(argv[2]) if len(argv) > 2 else 12)
        elif argv[0] == "rename" and len(argv) > 2:
            print("ok" if d.rename_session(argv[1], argv[2]) else "err not-found")
        elif argv[0] == "archive" and len(argv) > 1:
            print("ok" if d.archive_session(argv[1]) else "err not-found")
        elif argv[0] == "unarchive" and len(argv) > 1:
            print("ok" if d.unarchive_session(argv[1]) else "err not-found")
        elif argv[0] == "delete" and len(argv) > 2 and argv[2] == "yes":
            print("ok" if d.delete_session(argv[1]) else "err not-found")
        else:
            print("err usage", file=sys.stderr)
            return 1
    except d.DepotError as e:
        print("err " + str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
