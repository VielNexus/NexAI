from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agentx_api.config import config

router = APIRouter(tags=["coding-zone"])

Language = Literal["python", "javascript", "typescript", "shell", "lua", "cpp", "c", "go", "rust", "java", "html", "text"]

_SAFE_REL_RE = re.compile(r"^[A-Za-z0-9_./ -]{1,220}$")
_DENY_PARTS = {"", ".", "..", ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


def _root() -> Path:
    root = config.settings_path.parent / "coding_zone"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _sessions_root() -> Path:
    root = _root() / "sessions"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _now() -> float:
    return time.time()


def _slug(value: str, default: str = "coding-session") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_. -]+", "-", value.strip())[:64].strip(" .-")
    return cleaned or default


def _session_dir(session_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", session_id):
        raise HTTPException(status_code=400, detail="Invalid coding session id")
    return _sessions_root() / session_id


def _manifest_path(session_id: str) -> Path:
    return _session_dir(session_id) / "manifest.json"


def _files_dir(session_id: str) -> Path:
    path = _session_dir(session_id) / "files"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _runs_dir(session_id: str) -> Path:
    path = _session_dir(session_id) / "runs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _require_session(session_id: str) -> dict[str, Any]:
    manifest = _read_json(_manifest_path(session_id), {})
    if not manifest:
        raise HTTPException(status_code=404, detail="Coding session not found")
    return manifest


def _safe_rel_path(path: str) -> Path:
    raw = (path or "").strip().replace("\\\\", "/")
    if not raw or raw.endswith("/"):
        raise HTTPException(status_code=400, detail="File path is required")
    if not _SAFE_REL_RE.fullmatch(raw):
        raise HTTPException(status_code=400, detail="File path contains unsupported characters")
    parts = Path(raw).parts
    if any(part in _DENY_PARTS for part in parts):
        raise HTTPException(status_code=400, detail="File path contains denied path segment")
    rel = Path(*parts)
    if rel.is_absolute():
        raise HTTPException(status_code=400, detail="Absolute paths are not allowed")
    return rel


def _file_path(session_id: str, rel_path: str) -> Path:
    base = _files_dir(session_id).resolve()
    target = (base / _safe_rel_path(rel_path)).resolve()
    if base not in target.parents and target != base:
        raise HTTPException(status_code=400, detail="Path escapes coding session")
    return target


def _list_files(session_id: str) -> list[dict[str, Any]]:
    base = _files_dir(session_id)
    items: list[dict[str, Any]] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(base).as_posix()
        if any(part in _DENY_PARTS for part in Path(rel).parts):
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        items.append({"path": rel, "size": stat.st_size, "updated_at": stat.st_mtime})
    return items


def _infer_default_filename(language: str) -> str:
    return {
        "python": "main.py",
        "javascript": "main.js",
        "typescript": "main.ts",
        "shell": "main.sh",
        "lua": "main.lua",
        "cpp": "main.cpp",
        "c": "main.c",
        "go": "main.go",
        "rust": "main.rs",
        "java": "Main.java",
        "html": "index.html",
    }.get(language, "notes.txt")


def _default_content(language: str) -> str:
    return {
        "python": 'print("Hello from AgentX Coding Zone")\\n',
        "javascript": 'console.log("Hello from AgentX Coding Zone");\\n',
        "typescript": 'console.log("Hello from AgentX Coding Zone");\\n',
        "shell": 'echo "Hello from AgentX Coding Zone"\\n',
        "lua": 'print("Hello from AgentX Coding Zone")\\n',
        "cpp": '#include <iostream>\\nint main(){ std::cout << "Hello from AgentX Coding Zone\\\\n"; return 0; }\\n',
        "c": '#include <stdio.h>\\nint main(void){ printf("Hello from AgentX Coding Zone\\\\n"); return 0; }\\n',
        "go": 'package main\\nimport "fmt"\\nfunc main(){ fmt.Println("Hello from AgentX Coding Zone") }\\n',
        "rust": 'fn main() { println!("Hello from AgentX Coding Zone"); }\\n',
        "java": 'public class Main { public static void main(String[] args) { System.out.println("Hello from AgentX Coding Zone"); } }\\n',
        "html": '<!doctype html>\\n<html><body><h1>Hello from AgentX Coding Zone</h1></body></html>\\n',
    }.get(language, "")


def _command_for(language: str, rel_path: str) -> list[str] | None:
    if language == "python":
        return ["python3", rel_path]
    if language == "javascript":
        return ["node", rel_path]
    if language == "typescript":
        return ["bash", "-lc", f"if command -v ts-node >/dev/null 2>&1; then ts-node {rel_path}; else npx ts-node {rel_path}; fi"]
    if language == "shell":
        return ["bash", rel_path]
    if language == "lua":
        return ["lua", rel_path]
    if language == "cpp":
        return ["bash", "-lc", f"g++ -std=c++17 -O2 {rel_path} -o /tmp/agentx_coding_zone_cpp && /tmp/agentx_coding_zone_cpp"]
    if language == "c":
        return ["bash", "-lc", f"gcc -std=c11 -O2 {rel_path} -o /tmp/agentx_coding_zone_c && /tmp/agentx_coding_zone_c"]
    if language == "go":
        return ["go", "run", rel_path]
    if language == "rust":
        return ["bash", "-lc", f"rustc {rel_path} -o /tmp/agentx_coding_zone_rust && /tmp/agentx_coding_zone_rust"]
    if language == "java":
        return ["bash", "-lc", f"javac {rel_path} && java -cp $(dirname {rel_path}) Main"]
    return None


class CodingSessionCreate(BaseModel):
    title: str = Field(default="Untitled Coding Session", max_length=120)
    language: Language = "python"


class CodingFileWrite(BaseModel):
    path: str
    content: str = Field(default="", max_length=250_000)
    language: Language | None = None


class CodingRunRequest(BaseModel):
    path: str
    language: Language = "python"
    stdin: str = Field(default="", max_length=20_000)
    timeout_s: float = Field(default=10.0, ge=1.0, le=30.0)


@router.get("/coding-zone/languages")
def get_coding_zone_languages() -> dict[str, Any]:
    return {
        "languages": [
            {"id": "python", "label": "Python", "runnable": True},
            {"id": "javascript", "label": "JavaScript / Node", "runnable": True},
            {"id": "typescript", "label": "TypeScript", "runnable": True},
            {"id": "shell", "label": "Shell", "runnable": True},
            {"id": "lua", "label": "Lua", "runnable": True},
            {"id": "cpp", "label": "C++", "runnable": True},
            {"id": "c", "label": "C", "runnable": True},
            {"id": "go", "label": "Go", "runnable": True},
            {"id": "rust", "label": "Rust", "runnable": True},
            {"id": "java", "label": "Java", "runnable": True},
            {"id": "html", "label": "HTML", "runnable": False, "note": "Preview-only for now"},
            {"id": "text", "label": "Text", "runnable": False},
        ]
    }


@router.get("/coding-zone/sessions")
def list_coding_sessions() -> dict[str, Any]:
    sessions: list[dict[str, Any]] = []
    for manifest in sorted(_sessions_root().glob("*/manifest.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        payload = _read_json(manifest, {})
        if payload:
            payload["file_count"] = len(_list_files(str(payload.get("id", ""))))
            sessions.append(payload)
    return {"sessions": sessions}


@router.post("/coding-zone/sessions")
def create_coding_session(req: CodingSessionCreate) -> dict[str, Any]:
    session_id = uuid.uuid4().hex[:16]
    session_path = _session_dir(session_id)
    session_path.mkdir(parents=True, exist_ok=True)
    files_dir = _files_dir(session_id)
    default_file = _infer_default_filename(req.language)
    (files_dir / default_file).write_text(_default_content(req.language), encoding="utf-8")
    manifest = {
        "id": session_id,
        "title": _slug(req.title, "Untitled Coding Session"),
        "language": req.language,
        "created_at": _now(),
        "updated_at": _now(),
        "default_file": default_file,
    }
    _write_json(_manifest_path(session_id), manifest)
    return {"session": manifest, "files": _list_files(session_id)}


@router.get("/coding-zone/sessions/{session_id}")
def get_coding_session(session_id: str) -> dict[str, Any]:
    return {"session": _require_session(session_id), "files": _list_files(session_id)}


@router.delete("/coding-zone/sessions/{session_id}")
def delete_coding_session(session_id: str) -> dict[str, Any]:
    _require_session(session_id)
    shutil.rmtree(_session_dir(session_id), ignore_errors=True)
    return {"ok": True, "message": "Coding session deleted."}


@router.get("/coding-zone/sessions/{session_id}/file")
def get_coding_file(session_id: str, path: str) -> dict[str, Any]:
    _require_session(session_id)
    target = _file_path(session_id, path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Coding file not found")
    if target.stat().st_size > 250_000:
        raise HTTPException(status_code=413, detail="File is too large for Coding Zone editor")
    return {"path": _safe_rel_path(path).as_posix(), "content": target.read_text(encoding="utf-8", errors="replace"), "size": target.stat().st_size}


@router.put("/coding-zone/sessions/{session_id}/file")
def write_coding_file(session_id: str, req: CodingFileWrite) -> dict[str, Any]:
    manifest = _require_session(session_id)
    target = _file_path(session_id, req.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(req.content, encoding="utf-8")
    manifest["updated_at"] = _now()
    if req.language:
        manifest["language"] = req.language
    _write_json(_manifest_path(session_id), manifest)
    return {"ok": True, "path": _safe_rel_path(req.path).as_posix(), "size": target.stat().st_size, "files": _list_files(session_id)}


@router.delete("/coding-zone/sessions/{session_id}/file")
def delete_coding_file(session_id: str, path: str) -> dict[str, Any]:
    _require_session(session_id)
    target = _file_path(session_id, path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Coding file not found")
    target.unlink()
    return {"ok": True, "files": _list_files(session_id)}


@router.post("/coding-zone/sessions/{session_id}/run")
def run_coding_file(session_id: str, req: CodingRunRequest) -> dict[str, Any]:
    manifest = _require_session(session_id)
    target = _file_path(session_id, req.path)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="Coding file not found")
    if req.language in {"html", "text"}:
        raise HTTPException(status_code=400, detail=f"{req.language} is not runnable yet")

    rel = _safe_rel_path(req.path).as_posix()
    command = _command_for(req.language, rel)
    if not command:
        raise HTTPException(status_code=400, detail=f"No runner configured for language: {req.language}")

    started = _now()
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(_files_dir(session_id)), "NO_COLOR": "1"}
    try:
        proc = subprocess.run(
            command,
            cwd=str(_files_dir(session_id)),
            input=req.stdin,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=req.timeout_s,
            env=env,
            check=False,
        )
        exit_code = proc.returncode
        stdout = proc.stdout[-40_000:]
        stderr = proc.stderr[-40_000:]
        timed_out = False
    except FileNotFoundError as exc:
        exit_code = 127
        stdout = ""
        stderr = f"Runner not installed or unavailable: {exc}"
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        exit_code = -1
        stdout = (exc.stdout or "")[-40_000:] if isinstance(exc.stdout, str) else ""
        stderr = ((exc.stderr or "") if isinstance(exc.stderr, str) else "") + f"\\nTimed out after {req.timeout_s:.1f}s"
        stderr = stderr[-40_000:]
        timed_out = True

    result = {
        "id": uuid.uuid4().hex[:16],
        "session_id": session_id,
        "path": rel,
        "language": req.language,
        "command": command,
        "exit_code": exit_code,
        "ok": exit_code == 0,
        "stdout": stdout,
        "stderr": stderr,
        "duration_ms": int((_now() - started) * 1000),
        "timed_out": timed_out,
        "created_at": _now(),
    }
    _write_json(_runs_dir(session_id) / f"{result['id']}.json", result)
    manifest["updated_at"] = _now()
    _write_json(_manifest_path(session_id), manifest)
    return result


@router.get("/coding-zone/sessions/{session_id}/runs")
def list_coding_runs(session_id: str) -> dict[str, Any]:
    _require_session(session_id)
    runs = [_read_json(path, {}) for path in sorted(_runs_dir(session_id).glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)]
    return {"runs": [run for run in runs if run]}
