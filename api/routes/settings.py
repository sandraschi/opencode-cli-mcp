import json
import os
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["settings"])

# Settings live OUTSIDE the repo tree (never git-visible):
#   %LOCALAPPDATA%\opencode-cli-mcp\settings.json
_SETTINGS_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "opencode-cli-mcp"
_SETTINGS_FILE = _SETTINGS_DIR / "settings.json"
# Legacy location inside the repo (api/settings.json) - read-only migration
# source. Never written to again; safe to delete once migrated.
_LEGACY_FILE = Path(__file__).resolve().parent.parent / "settings.json"

_DEFAULTS = {
    "theme": "dark",
    "llm_provider": "local",
    "local_endpoint": "http://127.0.0.1:11434",
    "local_model": "llama3.2",
    "cloud_provider": "openai",
    "cloud_key": "",
    "cloud_model": "gpt-4o",
}

_REDACTED = "***"


def _load_settings() -> dict:
    """Load settings, preferring the LOCALAPPDATA file, falling back to the
    legacy repo-tree file for one-time migration, then defaults."""
    for candidate in (_SETTINGS_FILE, _LEGACY_FILE):
        if candidate.exists():
            try:
                data = json.loads(candidate.read_text())
                return {**_DEFAULTS, **data}
            except (json.JSONDecodeError, OSError):
                continue
    return dict(_DEFAULTS)


def _save_settings(data: dict):
    _SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(json.dumps(data, indent=2))


class SettingsUpdate(BaseModel):
    theme: str | None = None
    llm_provider: str | None = None
    local_endpoint: str | None = None
    local_model: str | None = None
    cloud_provider: str | None = None
    cloud_key: str | None = None
    cloud_model: str | None = None


@router.get("/settings")
async def get_settings():
    settings = _load_settings()
    # Never return the actual API key to the browser - presence flag only.
    settings["cloud_key"] = _REDACTED if settings.get("cloud_key") else ""
    return settings


@router.put("/settings")
async def update_settings(body: SettingsUpdate):
    settings = _load_settings()
    for key, val in body.model_dump(exclude_none=True).items():
        if key == "cloud_key" and val == _REDACTED:
            # Frontend echoed the redacted placeholder back - keep stored key.
            continue
        settings[key] = val
    _save_settings(settings)
    return {"success": True}
