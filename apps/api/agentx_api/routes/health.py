from __future__ import annotations

import os
import platform
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from agentx_api.config import config

router = APIRouter(prefix="/health", tags=["Health"])


def _git_commit(repo_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=repo_root,
            text=True,
            capture_output=True,
            timeout=2,
            check=False,
        )
        value = result.stdout.strip()
        return value or None
    except Exception:
        return None


def _git_branch(repo_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_root,
            text=True,
            capture_output=True,
            timeout=2,
            check=False,
        )
        value = result.stdout.strip()
        return value or None
    except Exception:
        return None


def _path_status(path: Path) -> dict[str, Any]:
    exists = path.exists()
    writable = False
    if exists:
        try:
            test_file = path / ".agentx-health-write-test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            writable = True
        except Exception:
            writable = False

    return {
        "path": str(path),
        "exists": exists,
        "writable": writable,
    }


def _tcp_check_from_url(url: str, timeout_s: float = 1.5) -> dict[str, Any]:
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if not host:
            return {"ok": False, "url": url, "error": "missing host"}

        start = time.perf_counter()
        with socket.create_connection((host, port), timeout=timeout_s):
            latency_ms = round((time.perf_counter() - start) * 1000, 2)

        return {
            "ok": True,
            "url": url,
            "host": host,
            "port": port,
            "latency_ms": latency_ms,
        }
    except Exception as exc:
        return {
            "ok": False,
            "url": url,
            "error": str(exc),
        }


@router.get("/full")
def full_health() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[3]
    diagnostics = config.runtime_diagnostics()

    fast_ollama = os.getenv("AGENTX_OLLAMA_FAST_BASE_URL") or os.getenv("AGENTX_FAST_OLLAMA_BASE_URL") or config.ollama_base_url
    heavy_ollama = os.getenv("AGENTX_OLLAMA_HEAVY_BASE_URL") or os.getenv("AGENTX_HEAVY_OLLAMA_BASE_URL") or ""

    ollama: dict[str, Any] = {
        "default": _tcp_check_from_url(config.ollama_base_url),
        "fast": _tcp_check_from_url(fast_ollama) if fast_ollama else None,
        "heavy": _tcp_check_from_url(heavy_ollama) if heavy_ollama else None,
    }

    workspace_root = Path(os.getenv("AGENTX_WORKSPACE_ROOT") or config.projects_dir)

    ok = not diagnostics.get("errors") and bool(ollama["default"]["ok"])

    return {
        "ok": ok,
        "version": "0.2.8-v10",
        "service": "agentx-api",
        "api": {
            "host": config.host,
            "port": config.port,
            "auth_enabled": config.auth_enabled,
            "rate_limit_enabled": config.rate_limit_enabled,
        },
        "git": {
            "branch": _git_branch(repo_root),
            "commit": _git_commit(repo_root),
        },
        "system": {
            "platform": platform.platform(),
            "python": platform.python_version(),
        },
        "ollama": ollama,
        "workspace": _path_status(workspace_root),
        "data": {
            "settings": str(config.settings_path),
            "threads": _path_status(config.threads_dir),
            "projects": _path_status(config.projects_dir),
            "scripts": _path_status(config.scripts_dir),
            "rag_db": str(config.rag_db_path),
        },
        "validation": {
            "available": True,
        },
        "diagnostics": diagnostics,
    }
