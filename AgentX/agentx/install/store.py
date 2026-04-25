from __future__ import annotations

import json
import os
from pathlib import Path

from agentx.install.models import ApiRuntimeConfig, AuthRuntimeConfig, InstallConfig, InstallProfile, ServiceMode, WebRuntimeConfig
from agentx.install.ollama import DEFAULT_OLLAMA_BASE_URL, normalize_ollama_base_url


def default_install_config_path() -> Path:
    xdg = (os.environ.get("XDG_CONFIG_HOME") or "").strip()
    if xdg:
        base = Path(xdg).expanduser()
    else:
        base = Path.home() / ".config"
    preferred = base / "agentx" / "install.json"
    legacy = base / "sol" / "install.json"
    if not preferred.exists() and legacy.exists():
        return legacy
    return preferred


def load_install_config(path: Path | None = None) -> InstallConfig:
    cfg_path = (path or default_install_config_path()).expanduser().resolve()
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    return InstallConfig(
        schema_version=int(data.get("schema_version", 1)),
        install_name=str(data.get("install_name", "default")),
        profile=InstallProfile(str(data["profile"])),
        service_mode=ServiceMode(str(data.get("service_mode", ServiceMode.NONE.value))),
        app_root=Path(str(data["app_root"])).expanduser().resolve(),
        runtime_root=Path(str(data["runtime_root"])).expanduser().resolve(),
        working_dir=Path(str(data["working_dir"])).expanduser().resolve(),
        config_path=Path(str(data["config_path"])).expanduser().resolve(),
        model_provider=str(data.get("model_provider", "ollama")).strip().lower() or "ollama",
        ollama_base_url=normalize_ollama_base_url(str(data.get("ollama_base_url", DEFAULT_OLLAMA_BASE_URL))),
        api=ApiRuntimeConfig(
            enabled=bool(data.get("api", {}).get("enabled", True)),
            host=str(data.get("api", {}).get("host", "127.0.0.1")),
            port=int(data.get("api", {}).get("port", 8420)),
        ),
        web=WebRuntimeConfig(
            enabled=bool(data.get("web", {}).get("enabled", False)),
            host=str(data.get("web", {}).get("host", "127.0.0.1")),
            port=int(data.get("web", {}).get("port", 5173)),
            open_browser=bool(data.get("web", {}).get("open_browser", False)),
        ),
        auth=AuthRuntimeConfig(
            enabled=bool(data.get("auth", {}).get("enabled", False)),
        ),
    )


def save_install_config(config: InstallConfig, path: Path | None = None) -> Path:
    cfg_path = (path or default_install_config_path()).expanduser().resolve()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(config.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return cfg_path
