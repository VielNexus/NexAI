from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path

import pytest


def _load_package_release_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "package_release.py"
    spec = importlib.util.spec_from_file_location("package_release", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load package_release.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    _write(repo / "install-agentx.sh", "#!/usr/bin/env bash\n")
    _write(repo / "README.md", "readme\n")
    _write(repo / "LICENSE", "license\n")
    _write(repo / "RELEASE.md", "release\n")
    _write(repo / "AgentX" / "pyproject.toml", '[project]\nname="agentx"\ndynamic=["version"]\n[tool.setuptools.dynamic]\nversion = {attr = "agentx.version.__version__"}\n')
    _write(repo / "AgentX" / "MANIFEST.in", "graft agentx\n")
    _write(repo / "AgentX" / "agentx" / "__init__.py", "from agentx.version import __version__\n")
    _write(repo / "AgentX" / "agentx" / "version.py", '__version__ = "1.2.3"\n')
    _write(repo / "apps" / "api" / "requirements.txt", "fastapi\n")
    _write(repo / "apps" / "api" / "agentx_api" / "__init__.py", "")
    _write(repo / "apps" / "api" / "agentx_api" / "data" / "settings.json", "{}\n")
    _write(repo / "apps" / "desktop" / "package.json", '{"name":"desktop"}')
    _write(repo / "AgentXWeb" / "package.json", '{"name":"agentx-web","private":true}')
    _write(repo / "AgentXWeb" / "src" / "main.tsx", "console.log('ok');\n")
    _write(repo / "AgentXWeb" / "dist" / "index.html", "<html></html>\n")
    _write(repo / "AgentXWeb" / "dist" / "assets" / "index.js", "console.log('dist');\n")

    _write(repo / ".git" / "config", "git\n")
    _write(repo / "AgentX" / ".venv" / "pyvenv.cfg", "venv\n")
    _write(repo / "apps" / "api" / ".venv" / "pyvenv.cfg", "venv\n")
    _write(repo / "AgentXWeb" / "node_modules" / "pkg" / "index.js", "node\n")
    _write(repo / "AgentX" / "data" / "runtime.db", "data\n")
    _write(repo / "AgentX" / "logs" / "install.log", "log\n")
    _write(repo / "AgentX" / "tests" / "test_anything.py", "def test_nope(): pass\n")
    _write(repo / ".vscode" / "settings.json", "{}\n")
    _write(repo / "AgentX" / "agentx.egg-info" / "PKG-INFO", "pkg\n")
    _write(repo / "AgentX" / "agentx" / "__pycache__" / "x.pyc", "pyc\n")
    return repo


def test_version_is_discovered_from_canonical_source(tmp_path: Path) -> None:
    module = _load_package_release_module()
    repo = _make_repo(tmp_path)
    assert module.discover_version(repo) == "1.2.3"


def test_collect_release_files_excludes_local_artifacts(tmp_path: Path) -> None:
    module = _load_package_release_module()
    repo = _make_repo(tmp_path)
    files = [path.as_posix() for path in module.collect_release_files(repo)]
    assert "install-agentx.sh" in files
    assert "AgentX/agentx/__init__.py" in files
    assert "AgentX/agentx/version.py" in files
    assert "apps/api/agentx_api/__init__.py" in files
    assert "AgentXWeb/dist/index.html" in files
    assert "apps/desktop/package.json" not in files
    assert "AgentXWeb/src/main.tsx" not in files
    assert ".git/config" not in files
    assert "AgentX/.venv/pyvenv.cfg" not in files
    assert "apps/api/.venv/pyvenv.cfg" not in files
    assert "AgentXWeb/node_modules/pkg/index.js" not in files
    assert "apps/api/agentx_api/data/settings.json" not in files
    assert "AgentX/data/runtime.db" not in files
    assert "AgentX/logs/install.log" not in files
    assert "AgentX/tests/test_anything.py" not in files


def test_package_release_fails_when_required_root_missing(tmp_path: Path) -> None:
    module = _load_package_release_module()
    repo = _make_repo(tmp_path)
    (repo / "AgentXWeb" / "dist" / "index.html").unlink()
    with pytest.raises(module.ReleasePackagingError, match="Missing required release paths"):
        module.package_release(repo, repo / "dist")


def test_default_archive_name_includes_version_and_writes_checksum(tmp_path: Path) -> None:
    module = _load_package_release_module()
    repo = _make_repo(tmp_path)
    result = module.package_release(repo, repo / "dist")
    assert result.archive_path.name == "agentx-1.2.3.zip"
    assert result.checksum_path.name == "agentx-1.2.3.zip.sha256"
    assert result.checksum_path.exists()
    checksum_text = result.checksum_path.read_text(encoding="utf-8")
    assert result.sha256 in checksum_text
    assert "agentx-1.2.3.zip" in checksum_text


def test_manifest_includes_version_and_sha256(tmp_path: Path) -> None:
    module = _load_package_release_module()
    repo = _make_repo(tmp_path)
    result = module.package_release(repo, repo / "dist")
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["version"] == "1.2.3"
    assert manifest["archive_name"] == "agentx-1.2.3.zip"
    assert manifest["sha256"] == result.sha256
    assert manifest["package_format"] == "zip"
    assert manifest["generated_at"]


def test_validate_archive_catches_forbidden_content(tmp_path: Path) -> None:
    module = _load_package_release_module()
    archive_path = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("install-agentx.sh", "")
        archive.writestr("AgentX/agentx/__init__.py", "")
        archive.writestr("apps/api/agentx_api/__init__.py", "")
        archive.writestr("AgentXWeb/dist/index.html", "")
        archive.writestr("release-manifest.json", "{}")
        archive.writestr(".git/config", "git")
    with pytest.raises(module.ReleasePackagingError, match="forbidden content"):
        module.validate_archive(archive_path)


def test_package_release_creates_expected_archive_layout(tmp_path: Path) -> None:
    module = _load_package_release_module()
    repo = _make_repo(tmp_path)
    result = module.package_release(repo, repo / "dist")
    assert result.archive_path.exists()
    with zipfile.ZipFile(result.archive_path, "r") as archive:
        names = set(archive.namelist())
        assert "install-agentx.sh" in names
        assert "AgentX/agentx/__init__.py" in names
        assert "AgentX/agentx/version.py" in names
        assert "apps/api/agentx_api/__init__.py" in names
        assert "AgentXWeb/dist/index.html" in names
        assert "release-manifest.json" in names
        assert "apps/desktop/package.json" not in names
        assert "AgentXWeb/src/main.tsx" not in names
        assert ".git/config" not in names
        assert "AgentX/.venv/pyvenv.cfg" not in names
        assert "apps/api/agentx_api/data/settings.json" not in names
        assert "AgentX/data/runtime.db" not in names
        assert "AgentX/logs/install.log" not in names
