from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["ollama-updates"])

CACHE_PATH = Path(__file__).resolve().parents[1] / "data" / "ollama_model_updates_cache.json"
CACHE_TTL_S = 6 * 60 * 60
OLLAMA_SEARCH_URL = "https://ollama.com/search"


class OllamaModelUpdate(BaseModel):
    name: str
    url: str
    description: str | None = None


class OllamaModelUpdatesResponse(BaseModel):
    ok: bool
    source: str
    fetched_at: float
    cached: bool
    models: list[OllamaModelUpdate]
    error: str | None = None


def _read_cache() -> dict[str, Any] | None:
    try:
        if not CACHE_PATH.exists():
            return None
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_cache(payload: dict[str, Any]) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        pass


def _parse_models(html: str) -> list[dict[str, str | None]]:
    seen: set[str] = set()
    models: list[dict[str, str | None]] = []
    for match in re.finditer(r'href="/(?:library/)?([A-Za-z0-9_.:-]+)"', html):
        name = match.group(1).strip()
        if not name or name in seen or name in {"search", "library", "signin", "download", "blog"}:
            continue
        if len(name) > 80:
            continue
        seen.add(name)
        models.append({"name": name, "url": f"https://ollama.com/library/{name}", "description": None})
        if len(models) >= 12:
            break
    return models


def _fetch_updates() -> OllamaModelUpdatesResponse:
    req = urllib.request.Request(
        OLLAMA_SEARCH_URL,
        headers={"User-Agent": "AgentX/1.0 (+local model update checker)", "Accept": "text/html,application/xhtml+xml"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=12.0) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    now = time.time()
    models = [OllamaModelUpdate(**item) for item in _parse_models(html)]
    return OllamaModelUpdatesResponse(ok=True, source=OLLAMA_SEARCH_URL, fetched_at=now, cached=False, models=models)


@router.get("/ollama/model-updates", response_model=OllamaModelUpdatesResponse)
def ollama_model_updates(refresh: bool = False) -> OllamaModelUpdatesResponse:
    now = time.time()
    cached = _read_cache()
    if cached and not refresh and now - float(cached.get("fetched_at", 0)) < CACHE_TTL_S:
        return OllamaModelUpdatesResponse(**{**cached, "cached": True})
    try:
        response = _fetch_updates()
        _write_cache(response.model_dump())
        return response
    except Exception as exc:
        if cached:
            return OllamaModelUpdatesResponse(**{**cached, "cached": True, "error": str(exc)})
        return OllamaModelUpdatesResponse(ok=False, source=OLLAMA_SEARCH_URL, fetched_at=now, cached=False, models=[], error=str(exc))
