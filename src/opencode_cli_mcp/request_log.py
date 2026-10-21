"""Bounded in-memory request log for the backend.

Why this exists: the CUA-NSIS smoke test can prove a page *rendered* (OCR) while
every one of its fetches silently failed - a title renders from client-side
routing whether or not data loads. The release gate therefore asks the backend
directly whether new HTTP requests arrived during the nav walk
(``GET /api/v1/request-log`` -> ``{"count": int, "requests": [...]}``).

Deliberately in-memory, bounded and not persisted: it is diagnostic evidence
for a smoke test, not an audit log. Restart the backend and it starts at zero.

Thread-safety: uvicorn serves concurrently, so the counter and ring share one
lock. Recording is O(1) and never blocks on I/O.
"""

import threading
import time
from collections import deque
from typing import Any

MAX_ENTRIES = 500
# Polling this endpoint must not inflate its own evidence.
EXEMPT_PATHS = ("/api/v1/request-log",)

_lock = threading.Lock()
_entries: deque[dict[str, Any]] = deque(maxlen=MAX_ENTRIES)
_total = 0


def record(method: str | None, path: str | None, status: int, duration_ms: float) -> None:
    """Append one completed HTTP request."""
    global _total
    with _lock:
        _total += 1
        _entries.append(
            {
                "ts": round(time.time(), 3),
                "method": (method or "").upper(),
                "path": path or "",
                "status": status,
                "ms": duration_ms,
            }
        )


def snapshot(limit: int = 200) -> dict[str, Any]:
    """Cumulative count plus the most recent entries (newest last)."""
    with _lock:
        items = list(_entries)[-max(1, limit) :]
        return {"count": _total, "requests": items}


def reset() -> None:
    """Clear the log (tests only)."""
    global _total
    with _lock:
        _entries.clear()
        _total = 0


def is_exempt(path: str) -> bool:
    return any(path == p or path.startswith(f"{p}/") for p in EXEMPT_PATHS)
