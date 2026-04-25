from __future__ import annotations

from pathlib import Path

from agentx.install.models import ApiRuntimeConfig, AuthRuntimeConfig, InstallConfig, InstallProfile, ServiceMode, WebRuntimeConfig
from agentx.install.store import default_install_config_path, load_install_config, save_install_config


def _config(tmp_path: Path) -> InstallConfig:
    return InstallConfig(
        schema_version=1,
        install_name="default",
        profile=InstallProfile.STANDARD,
        service_mode=ServiceMode.NONE,
        app_root=tmp_path / "app",
        runtime_root=tmp_path / "runtime",
        working_dir=tmp_path,
        config_path=tmp_path / "runtime" / "config" / "agentx.toml",
        model_provider="ollama",
        ollama_base_url="http://127.0.0.1:11434",
        api=ApiRuntimeConfig(enabled=True, host="0.0.0.0", port=8420),
        web=WebRuntimeConfig(enabled=True, host="0.0.0.0", port=5173),
        auth=AuthRuntimeConfig(enabled=False),
    )


def test_install_config_prefers_agentx_path_for_new_writes(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    legacy = tmp_path / "xdg-config" / "sol" / "install.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(_config(tmp_path).to_dict().__repr__(), encoding="utf-8")

    assert default_install_config_path() == tmp_path / "xdg-config" / "agentx" / "install.json"

    written = save_install_config(_config(tmp_path))
    assert written == tmp_path / "xdg-config" / "agentx" / "install.json"
    assert written.exists()


def test_load_install_config_falls_back_to_legacy_sol_path(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    legacy = tmp_path / "xdg-config" / "sol" / "install.json"
    legacy.parent.mkdir(parents=True)
    save_install_config(_config(tmp_path), legacy)

    loaded = load_install_config()
    assert loaded.app_root == (tmp_path / "app").resolve()
    assert loaded.api.host == "0.0.0.0"
    assert loaded.web.host == "0.0.0.0"


def test_install_sh_uses_current_repo_and_wsl_bind_defaults() -> None:
    text = Path("install.sh").read_text(encoding="utf-8")
    assert "https://github.com/VielNexus/NexAI.git" in text
    assert "https://github.com/VielAgentX/AgentX.git" not in text
    assert "default_service_bind_host" in text
    assert "AGENTX_API_HOST" in text
    assert "AGENTX_WEB_HOST" in text
    assert "--api-host \"$api_host\"" in text
    assert "--web-host \"$web_host\"" in text
    assert "--api-host 127.0.0.1" not in text
    assert "--web-host 127.0.0.1" not in text
