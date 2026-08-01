"""Ring-buffer log routes for the webapp Logs page.

Contract matched to web_sota/src/pages/Logging.tsx:
- GET  /api/logs?limit&offset&sort&level&kind&search&after_id
- GET  /api/logs/export?format=json|csv
- DELETE /api/logs
"""

import csv
import io

from fastapi import APIRouter, Query, Response

from api import logs

router = APIRouter(tags=["logs"])


@router.get("/logs")
async def get_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: str = Query("desc", pattern="^(asc|desc)$"),
    level: str | None = None,
    kind: str | None = None,
    search: str | None = None,
    after_id: str | None = None,
):
    page, total = logs.entries(
        limit=limit,
        offset=offset,
        level=level,
        kind=kind,
        search=search,
        sort=sort,
        after_id=after_id,
    )
    return {"entries": page, "total": total, "limit": limit, "offset": offset}


@router.get("/logs/export")
async def export_logs(
    format: str = Query("json", pattern="^(json|csv)$"),
    level: str | None = None,
    kind: str | None = None,
    search: str | None = None,
):
    items, _ = logs.entries(limit=logs.MAX_ENTRIES, offset=0, level=level, kind=kind, search=search, sort="asc")
    if format == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["timestamp", "level", "kind", "detail"])
        for e in items:
            writer.writerow([e["timestamp"], e["level"], e["kind"], e["detail"]])
        body = buf.getvalue()
        media = "text/csv"
        filename = "opencode-cli-mcp-logs.csv"
    else:
        import json

        body = json.dumps(items, indent=2, default=str)
        media = "application/json"
        filename = "opencode-cli-mcp-logs.json"
    return Response(
        content=body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/logs")
async def clear_logs():
    cleared = logs.clear()
    return {"success": True, "cleared": cleared}
