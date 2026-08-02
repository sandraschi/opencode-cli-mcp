from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from api.routes.settings import _load_settings

router = APIRouter(tags=["chat"])


async def _ollama_suggestion(endpoint: str, model: str) -> str:
    """On a model-not-found error, list the models Ollama actually has."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(f"{endpoint}/api/tags")
            if r.is_success:
                models = [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
                if models:
                    hint = ", ".join(models[:12])
                    return f" Model '{model}' not found. Available: {hint}"
    except Exception:
        pass
    return f" Model '{model}' not found on {endpoint}."


class ChatRequest(BaseModel):
    message: str
    system: str = ""
    # Frontend overrides: the Settings page selection (shared Zustand store /
    # localStorage) is authoritative over the server-side saved copy. When
    # omitted, the server-side settings are used as before.
    provider: str | None = None  # "local" | "cloud"
    model: str | None = None  # local model override (e.g. "gpt-oss:20b")
    endpoint: str | None = None  # local endpoint override (e.g. http://127.0.0.1:11434)


@router.post("/chat")
async def chat(body: ChatRequest):
    settings = _load_settings()
    provider = (body.provider or settings.get("llm_provider", "local")).lower()

    if provider == "local":
        endpoint = (body.endpoint or settings.get("local_endpoint", "http://127.0.0.1:11434")).rstrip("/")
        model = body.model or settings.get("local_model", "llama3.2")

        # LM Studio's default port is 1234. Parse the port properly - the
        # old substring check ("1234" in endpoint) misfired on e.g. :12340.
        try:
            is_lmstudio = urlsplit(endpoint).port == 1234
        except ValueError:
            is_lmstudio = False

        async with httpx.AsyncClient(timeout=120.0) as client:
            if is_lmstudio:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": body.system},
                        {"role": "user", "content": body.message},
                    ],
                    "temperature": 0.7,
                    "stream": False,
                }
                r = await client.post(
                    f"{endpoint}/v1/chat/completions",
                    json=payload,
                )
                if r.is_success:
                    data = r.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    return {"success": True, "response": content, "provider": "lmstudio", "model": model}
                return {"success": False, "response": f"LM Studio error: {r.status_code}", "provider": "lmstudio"}

            # Ollama — try /api/chat first (Ollama 0.5+), fallback to /api/generate
            try:
                r = await client.post(
                    f"{endpoint}/api/chat",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": body.system},
                            {"role": "user", "content": body.message},
                        ],
                        "stream": False,
                    },
                )
                if r.is_success:
                    data = r.json()
                    content = data.get("message", {}).get("content", "")
                    return {"success": True, "response": content, "provider": "ollama", "model": model}
            except Exception:
                pass

            # Fallback to /api/generate (older Ollama)
            prompt = f"{body.system}\n\n{body.message}" if body.system else body.message
            r = await client.post(
                f"{endpoint}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            if r.is_success:
                data = r.json()
                content = data.get("response", "")
                return {"success": True, "response": content, "provider": "ollama", "model": model}

            detail = await _ollama_suggestion(endpoint, model) if r.status_code == 404 else ""
            return {
                "success": False,
                "response": f"Ollama error: {r.status_code}.{detail}",
                "provider": "ollama",
            }  # noqa: E501

    # Cloud provider
    cloud_provider = settings.get("cloud_provider", "openai")
    cloud_key = settings.get("cloud_key", "")
    cloud_model = settings.get("cloud_model", "gpt-4o")

    if not cloud_key:
        return {
            "success": False,
            "response": "Cloud API key not configured. Set it in Settings.",
            "provider": cloud_provider,
        }  # noqa: E501

    base_urls = {
        "openai": "https://api.openai.com/v1",
        "anthropic": "https://api.anthropic.com/v1",
        "google": "https://generativelanguage.googleapis.com/v1beta",
        "openrouter": "https://openrouter.ai/api/v1",
    }

    base_url = base_urls.get(cloud_provider, base_urls["openai"])

    async with httpx.AsyncClient(timeout=120.0) as client:
        if cloud_provider == "anthropic":
            r = await client.post(
                f"{base_url}/messages",
                headers={"x-api-key": cloud_key, "anthropic-version": "2023-06-01"},
                json={
                    "model": cloud_model,
                    "max_tokens": 4096,
                    "system": body.system,
                    "messages": [{"role": "user", "content": body.message}],
                },
            )
            if r.is_success:
                data = r.json()
                content = data.get("content", [{}])[0].get("text", "")
                return {"success": True, "response": content, "provider": cloud_provider, "model": cloud_model}
            return {
                "success": False,
                "response": f"Anthropic error: {r.status_code} {r.text}",
                "provider": cloud_provider,
            }  # noqa: E501

        if cloud_provider == "google":
            r = await client.post(
                f"{base_url}/models/{cloud_model}:generateContent",
                params={"key": cloud_key},
                json={
                    "system_instruction": {"parts": [{"text": body.system}]},
                    "contents": [{"parts": [{"text": body.message}]}],
                },
            )
            if r.is_success:
                data = r.json()
                content = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                return {"success": True, "response": content, "provider": cloud_provider, "model": cloud_model}
            return {"success": False, "response": f"Google error: {r.status_code} {r.text}", "provider": cloud_provider}

        # OpenAI / OpenRouter (OpenAI-compatible)
        headers = {"Authorization": f"Bearer {cloud_key}"}
        r = await client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json={
                "model": cloud_model,
                "messages": [
                    {"role": "system", "content": body.system},
                    {"role": "user", "content": body.message},
                ],
                "temperature": 0.7,
            },
        )
        if r.is_success:
            data = r.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"success": True, "response": content, "provider": cloud_provider, "model": cloud_model}
        return {
            "success": False,
            "response": f"{cloud_provider} error: {r.status_code} {r.text}",
            "provider": cloud_provider,
        }  # noqa: E501
