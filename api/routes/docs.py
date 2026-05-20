from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["docs"])

DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "docs"
README_PATH = Path(__file__).resolve().parent.parent.parent / "README.md"
CLAUDE_PATH = Path(__file__).resolve().parent.parent.parent / "CLAUDE.md"

DOC_SOURCES: list[dict[str, str]] = []


def _refresh_doc_list():
    global DOC_SOURCES
    sources = [
        {"id": "README", "path": str(README_PATH), "label": "Project Overview", "file": "README.md"},
        {"id": "CLAUDE", "path": str(CLAUDE_PATH), "label": "CLAUDE.md", "file": "CLAUDE.md"},
    ]
    if DOCS_DIR.is_dir():
        for f in sorted(DOCS_DIR.iterdir()):
            if f.suffix == ".md":
                label = f.stem.replace("-", " ").replace("_", " ").title()
                sources.append({
                    "id": f.stem,
                    "path": str(f),
                    "label": label,
                    "file": f"docs/{f.name}",
                })
    DOC_SOURCES = sources


_refresh_doc_list()


@router.get("/docs")
async def list_docs():
    _refresh_doc_list()
    items = [{"id": d["id"], "label": d["label"], "file": d["file"]} for d in DOC_SOURCES]
    return {"success": True, "data": {"docs": items}}


@router.get("/docs/{doc_id}")
async def get_doc(doc_id: str):
    _refresh_doc_list()
    match = [d for d in DOC_SOURCES if d["id"].lower() == doc_id.lower()]
    if not match:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")
    try:
        content = Path(match[0]["path"]).read_text(encoding="utf-8")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to read document: {e}")
    return {"success": True, "data": {"id": match[0]["id"], "label": match[0]["label"], "content": content}}
