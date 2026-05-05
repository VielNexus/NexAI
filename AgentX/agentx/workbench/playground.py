from __future__ import annotations

from pathlib import Path
from typing import Any

from agentx.workbench.analyzer import analyze_zip


def import_and_analyze_zip(
    zip_path: str | Path,
    workspace_root: str | Path,
    *,
    name: str | None = None,
) -> dict[str, Any]:
    return analyze_zip(zip_path, workspace_root, name)


def import_and_analyze_archive(
    archive_path: str | Path,
    workspace_root: str | Path,
    *,
    name: str | None = None,
    project_name: str | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Compatibility wrapper for WebUI archive uploads.

    Older routes used project_name= while the ZIP analyzer uses name=.
    Normalize both names here.
    """
    chosen_name = name or project_name
    return import_and_analyze_zip(
        archive_path,
        workspace_root,
        name=chosen_name,
    )
