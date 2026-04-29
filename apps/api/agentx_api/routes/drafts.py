from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agentx.core.llm import OllamaConfig, ProviderError, ollama_generate, provider_error_detail
from agentx_api.config import config
from agentx_api.ollama import normalize_ollama_base_url
from agentx_api.routes.settings import _read_settings, effective_ollama_endpoint_base_url, effective_ollama_request_timeout_s

router = APIRouter(tags=["drafts"])

DraftMode = Literal["open", "explain", "rewrite", "explain_and_rewrite"]
MAX_DRAFT_CHARS = 100_000


class DraftGenerateRequest(BaseModel):
    mode: DraftMode = "explain_and_rewrite"
    filename: str | None = None
    language: str | None = None
    content: str = Field(min_length=1)


class DraftGenerateResponse(BaseModel):
    title: str
    language: str
    original: str
    explanation: str
    improved: str
    notes: list[str]
    model_provider: str | None = None
    model_name: str | None = None
    generated_at: float


def _clean_text(value: str | None, *, max_len: int = 160) -> str:
    raw = (value or "").strip()
    raw = re.sub(r"[\x00-\x1f\x7f]+", " ", raw)
    raw = re.sub(r"\s+", " ", raw)
    return raw[:max_len].strip()


class PathLike:
    def __init__(self, value: str | None):
        self.value = (value or "").strip()

    @property
    def suffix(self) -> str:
        name = self.value.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        if "." not in name:
            return ""
        return name.rsplit(".", 1)[-1].lower()


def _infer_language(filename: str | None, language: str | None, content: str) -> str:
    lang = _clean_text(language, max_len=40).lower()
    if lang and lang not in {"auto", "text", "plain"}:
        aliases = {"py": "python", "js": "javascript", "ts": "typescript", "yml": "yaml", "md": "markdown", "htm": "html"}
        return aliases.get(lang, lang)
    suffix = PathLike(filename).suffix
    ext_map = {
        "py": "python",
        "lua": "lua",
        "js": "javascript",
        "ts": "typescript",
        "html": "html",
        "htm": "html",
        "css": "css",
        "xml": "xml",
        "php": "php",
        "java": "java",
        "json": "json",
        "yaml": "yaml",
        "yml": "yaml",
        "md": "markdown",
        "sql": "sql",
        "sh": "bash",
        "bash": "bash",
    }
    if suffix in ext_map:
        return ext_map[suffix]
    sample = content.lstrip()[:400].lower()
    if sample.startswith("<?php"):
        return "php"
    if sample.startswith("<!doctype html") or "<html" in sample[:200]:
        return "html"
    if sample.startswith("<?xml"):
        return "xml"
    if "function oncreature" in sample or "npchandler" in sample:
        return "lua"
    return "text"


def _title_for(filename: str | None, language: str) -> str:
    name = _clean_text(filename, max_len=90) or f"{language.title()} Draft"
    return f"{name} Draft"


def _fallback_draft(req: DraftGenerateRequest, language: str) -> DraftGenerateResponse:
    content = req.content.strip()
    explanation = ""
    improved = ""
    if req.mode in {"open", "explain", "explain_and_rewrite"}:
        explanation = "This draft was opened locally. The model provider is not configured, so AgentX preserved the original content and prepared it for review."
    if req.mode in {"rewrite", "explain_and_rewrite"}:
        improved = content
    return DraftGenerateResponse(
        title=_title_for(req.filename, language),
        language=language,
        original=content,
        explanation=explanation,
        improved=improved,
        notes=["No chat model is configured, so this is a local-only draft shell.", "Configure an Ollama or OpenAI model to generate explanations and rewrites."],
        model_provider="stub",
        model_name="stub",
        generated_at=time.time(),
    )


def _draft_prompt(req: DraftGenerateRequest, language: str) -> str:
    mode_instructions = {
        "open": "Create a clean draft workspace. Explain what the content is and add practical notes. Only rewrite if the original has obvious formatting problems.",
        "explain": "Explain the code or document clearly, section by section. Keep the improved version empty unless a tiny clarity rewrite is necessary.",
        "rewrite": "Rewrite the content into a cleaner, more maintainable version. Preserve behavior and call out assumptions.",
        "explain_and_rewrite": "Explain the content clearly, then provide a cleaner rewritten version that preserves behavior.",
    }
    filename = _clean_text(req.filename, max_len=120) or "untitled"
    return f'''You are AgentX Draft Workspace.

Task mode: {req.mode}
Filename: {filename}
Detected language: {language}

Rules:
- Preserve the target language and original intent.
- Do not invent unsupported framework APIs.
- If this is game-server or Tibia/TFS Lua, keep compatibility assumptions explicit.
- Do not include fake dialogue or the phrase Copy code.
- Return ONLY valid JSON, no markdown wrapper.
- JSON shape exactly:
  {{
    "title": "short useful draft title",
    "language": "{language}",
    "explanation": "clear explanation using paragraphs or bullets",
    "improved": "rewritten content, or empty string if not requested",
    "notes": ["short note", "short note"]
  }}

Instruction:
{mode_instructions.get(req.mode, mode_instructions['explain_and_rewrite'])}

Original content:
```{language}
{req.content}
```
'''


def _openai_generate(prompt: str, model: str) -> str:
    url = f"{config.openai_base_url.rstrip('/')}/v1/chat/completions"
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2}
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {config.openai_api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=config.openai_timeout_s) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return str(data["choices"][0]["message"]["content"])
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if getattr(e, "fp", None) else ""
        raise HTTPException(status_code=502, detail=f"OpenAI HTTP {e.code}: {body}") from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"OpenAI request failed: {e}") from e


def _provider_generate(prompt: str) -> tuple[str, str, str]:
    settings = _read_settings()
    provider = (getattr(settings, "chatProvider", None) or ("openai" if config.openai_api_key else "stub")).strip().lower()
    model = (getattr(settings, "chatModel", None) or (config.openai_model if config.openai_api_key else "stub")).strip()
    if provider == "stub" or not model or model == "stub":
        return "", "stub", "stub"
    if provider == "openai":
        if not config.openai_api_key:
            raise HTTPException(status_code=400, detail="OpenAI is selected but AGENTX_OPENAI_API_KEY is not set.")
        return _openai_generate(prompt, model), provider, model
    if provider == "ollama":
        endpoint = getattr(settings, "ollamaDraftEndpoint", "default") if getattr(settings, "ollamaMultiEndpointEnabled", False) else "default"
        base_url = normalize_ollama_base_url(effective_ollama_endpoint_base_url(settings, endpoint))
        try:
            text = ollama_generate(
                cfg=OllamaConfig(
                    base_url=base_url,
                    model=model,
                    timeout_s=effective_ollama_request_timeout_s(settings),
                    max_tool_iters=max(1, int(getattr(config, "ollama_tool_max_iters", 4))),
                ),
                prompt=prompt,
            )
            return text, provider, model
        except ProviderError as exc:
            detail = provider_error_detail(exc) or {"message": str(exc)}
            raise HTTPException(status_code=502, detail=detail) from exc
    raise HTTPException(status_code=400, detail=f"Unsupported draft provider: {provider}")


def _extract_json(text: str) -> dict:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(raw[start : end + 1])
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {"title": "Draft", "explanation": raw, "improved": "", "notes": ["Model did not return structured JSON; showing the raw response as the explanation."]}


@router.post("/drafts/generate", response_model=DraftGenerateResponse)
def generate_draft(req: DraftGenerateRequest) -> DraftGenerateResponse:
    content = (req.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Draft content is required.")
    if len(content) > MAX_DRAFT_CHARS:
        raise HTTPException(status_code=413, detail=f"Draft content is too large. Limit is {MAX_DRAFT_CHARS} characters.")
    req = req.model_copy(update={"content": content})
    language = _infer_language(req.filename, req.language, content)
    text, provider, model = _provider_generate(_draft_prompt(req, language))
    if provider == "stub":
        return _fallback_draft(req, language)
    data = _extract_json(text)
    notes_raw = data.get("notes")
    notes = [str(item).strip() for item in notes_raw if str(item).strip()] if isinstance(notes_raw, list) else []
    if not notes:
        notes = ["Generated by AgentX Draft Workspace."]
    return DraftGenerateResponse(
        title=_clean_text(data.get("title"), max_len=120) or _title_for(req.filename, language),
        language=_clean_text(data.get("language"), max_len=40) or language,
        original=content,
        explanation=str(data.get("explanation") or "").strip(),
        improved=str(data.get("improved") or "").strip(),
        notes=notes[:12],
        model_provider=provider,
        model_name=model,
        generated_at=time.time(),
    )
