"""In-memory ring-buffer log store for the webapp Logs page.

Fleet pattern (logging backends on ports 11060-11068): a process-local
ring buffer keeps the last N events; the /api/logs routes serve, export,
and clear it. This process is the FastAPI backend, so it records API
traffic (via a request middleware) plus explicit log() calls.
"""

import datetime
import itertools
import threading
from collections import deque

MAX_ENTRIES = 2000

_buffer: deque[dict] = deque(maxlen=MAX_ENTRIES)
_ids = itertools.count(1)
_lock = threading.Lock()


def log(level: str, kind: str, detail: str, **meta) -> dict:
    entry = {
        "id": str(next(_ids)),
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "level": level.upper(),
        "kind": kind,
        "detail": detail,
        "meta": meta,
    }
    with _lock:
        _buffer.append(entry)
    return entry


def entries(
    limit: int = 50,
    offset: int = 0,
    level: str | None = None,
    kind: str | None = None,
    search: str | None = None,
    sort: str = "desc",
    after_id: str | None = None,
) -> tuple[list[dict], int]:
    with _lock:
        items = list(_buffer)
    if level:
        items = [e for e in items if e["level"] == level.upper()]
    if kind:
        items = [e for e in items if e["kind"] == kind]
    if search:
        needle = search.lower()
        items = [e for e in items if needle in e["detail"].lower()]

    if after_id is not None:
        # Tail mode: ascending (oldest first) so the UI can append after the
        # last known id without reordering.
        items = [e for e in items if int(e["id"]) > int(after_id)]
        return items, len(items)

    if sort == "asc":
        items = list(items)
    else:
        items = list(reversed(items))  # desc: newest first
    total = len(items)
    return items[offset : offset + limit], total


def clear() -> int:
    with _lock:
        n = len(_buffer)
        _buffer.clear()
    return n
