import json
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["settings"])

_SETTINGS_FILE = Path(__file__).resolve().parent.parent / "settings.json"


def _load_settings() -> dict:
    if _SETTINGS_FILE.exists():
        try:
            return json.loads(_SETTINGS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "theme": "dark",
        "llm_provider": "local",
        "local_endpoint": "http://127.0.0.1:11434",
        "local_model": "llama3.2",
        "cloud_provider": "openai",
        "cloud_key": "",
        "cloud_model": "gpt-4o",
    }


def _save_settings(data: dict):
    _SETTINGS_FILE.write_text(json.dumps(data, indent=2))


_settings = _load_settings()


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
    return _settings


@router.put("/settings")
async def update_settings(body: SettingsUpdate):
    for key, val in body.model_dump(exclude_none=True).items():
        _settings[key] = val
    _save_settings(_settings)
    return {"success": True}
