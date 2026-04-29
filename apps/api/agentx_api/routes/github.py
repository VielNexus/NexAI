from __future__ import annotations

import os
import subprocess
import tarfile
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["github"])

REPO_ROOT = Path(__file__).resolve().parents[4]
BACKUP_ROOT = Path(os.environ.get("AGENTX_BACKUP_DIR", str(Path.home() / "agentx-backups"))).expanduser()


class GitHubStatusResponse(BaseModel):
    ok: bool
    repo_exists: bool
    branch: str | None = None
    local_commit: str | None = None
    remote_commit: str | None = None
    remote_ref: str | None = None
    is_up_to_date: bool = False
    dirty: bool = False
    ahead: int = 0
    behind: int = 0
    message: str | None = None
    checked_at: float


class GitHubUpdateRequest(BaseModel):
    remote: str = "origin"
    branch: str | None = None


class GitHubUpdateResponse(BaseModel):
    ok: bool
    backup_path: str | None = None
    before: GitHubStatusResponse
    after: GitHubStatusResponse | None = None
    output: str = ""
    message: str


def _run_git(args: list[str], *, timeout_s: float = 30.0, check: bool = False) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_s,
        check=False,
    )
    if check and proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "git command failed").strip())
    return proc


def _git_text(args: list[str], *, timeout_s: float = 30.0) -> str:
    return _run_git(args, timeout_s=timeout_s, check=True).stdout.strip()


def _repo_exists() -> bool:
    return (REPO_ROOT / ".git").exists()


def _status(remote: str = "origin", branch: str | None = None, *, fetch: bool = False) -> GitHubStatusResponse:
    now = time.time()
    if not _repo_exists():
        return GitHubStatusResponse(ok=False, repo_exists=False, message=f"No Git repo found at {REPO_ROOT}", checked_at=now)
    try:
        current_branch = branch or _git_text(["rev-parse", "--abbrev-ref", "HEAD"])
        if fetch:
            _run_git(["fetch", remote, current_branch], timeout_s=45.0)
        local_commit = _git_text(["rev-parse", "HEAD"])
        remote_ref = f"{remote}/{current_branch}"
        remote_commit_proc = _run_git(["rev-parse", "--verify", remote_ref], timeout_s=10.0)
        remote_commit = remote_commit_proc.stdout.strip() if remote_commit_proc.returncode == 0 else None
        dirty = bool(_git_text(["status", "--porcelain"]))
        ahead = 0
        behind = 0
        if remote_commit:
            counts = _git_text(["rev-list", "--left-right", "--count", f"HEAD...{remote_ref}"])
            parts = counts.split()
            if len(parts) == 2:
                ahead, behind = int(parts[0]), int(parts[1])
        is_up_to_date = bool(remote_commit and local_commit == remote_commit and not dirty)
        if dirty:
            message = "Local uncommitted changes are present."
        elif behind:
            message = f"Update available: local branch is behind by {behind} commit(s)."
        elif ahead:
            message = f"Local branch is ahead by {ahead} commit(s)."
        elif is_up_to_date:
            message = "Local checkout matches GitHub."
        else:
            message = "GitHub status could not be fully determined."
        return GitHubStatusResponse(
            ok=True,
            repo_exists=True,
            branch=current_branch,
            local_commit=local_commit,
            remote_commit=remote_commit,
            remote_ref=remote_ref,
            is_up_to_date=is_up_to_date,
            dirty=dirty,
            ahead=ahead,
            behind=behind,
            message=message,
            checked_at=now,
        )
    except Exception as exc:
        return GitHubStatusResponse(ok=False, repo_exists=True, message=str(exc), checked_at=now)


def _backup_repo() -> str:
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = BACKUP_ROOT / f"pre-github-update-{stamp}.tar.gz"
    exclude_names = {".git", ".venv", "node_modules", "dist", "__pycache__", ".pytest_cache", "logs", "cache", "tmp", "work", "run", "memory", "cleanup-backups"}
    with tarfile.open(target, "w:gz") as tar:
        for item in REPO_ROOT.iterdir():
            if item.name in exclude_names:
                continue
            tar.add(item, arcname=f"AgentX/{item.name}")
    return str(target)


@router.get("/github/status", response_model=GitHubStatusResponse)
def github_status(fetch: bool = True) -> GitHubStatusResponse:
    return _status(fetch=fetch)


@router.post("/github/update", response_model=GitHubUpdateResponse)
def github_update(req: GitHubUpdateRequest) -> GitHubUpdateResponse:
    before = _status(remote=req.remote, branch=req.branch, fetch=True)
    if not before.repo_exists:
        raise HTTPException(status_code=404, detail=before.message or "No Git repo found.")
    backup_path = _backup_repo()
    if before.dirty:
        return GitHubUpdateResponse(
            ok=False,
            backup_path=backup_path,
            before=before,
            after=None,
            output="",
            message="Backup created, but update was not applied because local uncommitted changes are present.",
        )
    branch = req.branch or before.branch or "main"
    pull = _run_git(["pull", "--ff-only", req.remote, branch], timeout_s=90.0)
    output = "\n".join(part for part in [pull.stdout.strip(), pull.stderr.strip()] if part)
    after = _status(remote=req.remote, branch=branch, fetch=False)
    if pull.returncode != 0:
        return GitHubUpdateResponse(ok=False, backup_path=backup_path, before=before, after=after, output=output, message="Backup created, but git pull failed.")
    return GitHubUpdateResponse(ok=True, backup_path=backup_path, before=before, after=after, output=output, message="GitHub update applied. Restart AgentX services if files changed.")
