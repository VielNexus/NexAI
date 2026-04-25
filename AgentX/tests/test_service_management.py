from __future__ import annotations

import subprocess
from pathlib import Path

from agentx.cli import build_parser, main as cli_main
from agentx.install.lifecycle import (
    autostart_state_from_services,
    compute_install_paths,
    disable_systemd_units,
    enable_systemd_units,
    install_systemd_units,
    read_service_logs,
    service_log_paths,
    status_installation,
    systemctl_user,
    systemd_status,
    systemd_user_available_or_error,
)
from agentx.install.models import InstallProfile, ServiceMode
from agentx.install.platform import detect_platform
from agentx.install.store import save_install_config
from agentx.install.wizard import build_install_config


def _config(tmp_path: Path) -> object:
    app_root = tmp_path / "app"
    (app_root / "AgentX" / "plugins").mkdir(parents=True)
    (app_root / "AgentX" / "skills").mkdir(parents=True)
    (app_root / "AgentX" / "Server" / "data" / "features").mkdir(parents=True)
    (app_root / "apps" / "api" / "agentx_api").mkdir(parents=True)
    (app_root / "AgentXWeb" / "dist").mkdir(parents=True)
    (app_root / "AgentXWeb" / "dist" / "index.html").write_text("ok", encoding="utf-8")
    return build_install_config(
        app_root=app_root,
        runtime_root=tmp_path / "runtime",
        working_dir=tmp_path / "work",
        profile=InstallProfile.STANDARD,
        model_provider="stub",
        api_host="127.0.0.1",
        api_port=8420,
        web_host="127.0.0.1",
        web_port=5173,
        service_mode=ServiceMode.SYSTEMD_USER,
    )


def test_build_install_config_defaults_auth_disabled(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert config.auth.enabled is False


def test_detect_platform_reports_present_but_unusable(monkeypatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("platform.release", lambda: "6.6.0-microsoft-standard-WSL2")
    monkeypatch.setattr("platform.version", lambda: "Linux")
    monkeypatch.setattr("pathlib.Path.exists", lambda self: str(self) == "/proc/version")
    monkeypatch.setattr("pathlib.Path.read_text", lambda self, **kwargs: "Linux version 6.6.0-microsoft-standard-WSL2")
    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/systemctl" if cmd == "systemctl" else None)
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout="", stderr="Failed to connect to bus"),
    )
    info = detect_platform()
    assert info.is_wsl is True
    assert info.systemd_user_available is False
    assert info.systemd_present_but_unusable is True
    assert info.no_systemd is False


def test_systemd_user_available_or_error_raises_clear_error(monkeypatch) -> None:
    platform_info = type(
        "Platform",
        (),
        {"systemd_user_available": False, "systemd_present_but_unusable": True, "no_systemd": False},
    )()
    monkeypatch.setattr("agentx.install.lifecycle.detect_platform", lambda: platform_info)
    try:
        systemd_user_available_or_error()
    except RuntimeError as exc:
        assert "systemctl --user is present but not usable" in str(exc)
    else:
        raise AssertionError("Expected unusable systemd-user environment to fail")


def test_systemctl_user_fails_loudly(monkeypatch) -> None:
    platform_info = type(
        "Platform",
        (),
        {"systemd_user_available": True, "systemd_present_but_unusable": False, "no_systemd": False},
    )()
    monkeypatch.setattr("agentx.install.lifecycle.detect_platform", lambda: platform_info)
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout="", stderr="unit missing"),
    )
    try:
        systemctl_user("start", "agentx-api.service")
    except RuntimeError as exc:
        assert "systemctl --user start agentx-api.service failed" in str(exc)
    else:
        raise AssertionError("Expected systemctl failure to raise")


def test_install_systemd_units_writes_units_and_reloads(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    paths = compute_install_paths(config)
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr("agentx.install.lifecycle.default_install_config_path", lambda: tmp_path / "install.json")
    monkeypatch.setattr(
        "agentx.install.lifecycle.detect_platform",
        lambda: type("Platform", (), {"systemd_user_available": True, "systemd_present_but_unusable": False, "no_systemd": False})(),
    )
    monkeypatch.setattr(
        "agentx.install.lifecycle.subprocess.run",
        lambda args, **kwargs: calls.append(tuple(args)) or subprocess.CompletedProcess(args, 0, stdout="", stderr=""),
    )
    written = install_systemd_units(config, paths)
    assert any(path.name == "agentx-api.service" for path in written)
    assert any(path.name == "agentx-web.service" for path in written)
    api_unit = next(path for path in written if path.name == "agentx-api.service").read_text(encoding="utf-8")
    web_unit = next(path for path in written if path.name == "agentx-web.service").read_text(encoding="utf-8")
    for unit_text in (api_unit, web_unit):
        unit_section = unit_text.split("[Service]", 1)[0]
        service_section = unit_text.split("[Service]", 1)[1]
        assert "Restart=on-failure" in unit_text
        assert "RestartSec=3" in unit_text
        assert "StartLimitIntervalSec=60" in unit_section
        assert "StartLimitBurst=5" in unit_section
        assert "StartLimitIntervalSec=60" not in service_section
        assert "StartLimitBurst=5" not in service_section
        assert "TimeoutStartSec=30" in unit_text
        assert "TimeoutStopSec=20" in unit_text
    assert ("systemctl", "--user", "daemon-reload") in calls


def test_enable_systemd_units_verifies_enabled_state(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    calls: list[tuple[str, ...]] = []
    responses = {
        ("systemctl", "--user", "enable", "agentx-api.service", "agentx-web.service"): subprocess.CompletedProcess([], 0, stdout="", stderr=""),
        ("systemctl", "--user", "is-enabled", "agentx-api.service"): subprocess.CompletedProcess([], 0, stdout="enabled\n", stderr=""),
        ("systemctl", "--user", "is-enabled", "agentx-web.service"): subprocess.CompletedProcess([], 0, stdout="enabled\n", stderr=""),
    }
    monkeypatch.setattr(
        "agentx.install.lifecycle.detect_platform",
        lambda: type("Platform", (), {"systemd_user_available": True, "systemd_present_but_unusable": False, "no_systemd": False})(),
    )
    monkeypatch.setattr(
        "agentx.install.lifecycle.subprocess.run",
        lambda args, **kwargs: calls.append(tuple(args)) or responses[tuple(args)],
    )
    states = enable_systemd_units(config)
    assert states == {"agentx-api.service": "enabled", "agentx-web.service": "enabled"}
    assert ("systemctl", "--user", "is-enabled", "agentx-api.service") in calls
    assert ("systemctl", "--user", "is-enabled", "agentx-web.service") in calls


def test_disable_systemd_units_verifies_disabled_state(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    calls: list[tuple[str, ...]] = []
    responses = {
        ("systemctl", "--user", "disable", "agentx-api.service", "agentx-web.service"): subprocess.CompletedProcess([], 0, stdout="", stderr=""),
        ("systemctl", "--user", "is-enabled", "agentx-api.service"): subprocess.CompletedProcess([], 1, stdout="disabled\n", stderr=""),
        ("systemctl", "--user", "is-enabled", "agentx-web.service"): subprocess.CompletedProcess([], 1, stdout="disabled\n", stderr=""),
    }
    monkeypatch.setattr(
        "agentx.install.lifecycle.detect_platform",
        lambda: type("Platform", (), {"systemd_user_available": True, "systemd_present_but_unusable": False, "no_systemd": False})(),
    )
    monkeypatch.setattr(
        "agentx.install.lifecycle.subprocess.run",
        lambda args, **kwargs: calls.append(tuple(args)) or responses[tuple(args)],
    )
    states = disable_systemd_units(config)
    assert states == {"agentx-api.service": "disabled", "agentx-web.service": "disabled"}
    assert ("systemctl", "--user", "is-enabled", "agentx-api.service") in calls
    assert ("systemctl", "--user", "is-enabled", "agentx-web.service") in calls


def test_service_log_paths_returns_api_and_web(tmp_path: Path) -> None:
    config = _config(tmp_path)
    paths = compute_install_paths(config)
    logs = service_log_paths(paths)
    assert logs["api"] == paths.api_log_path
    assert logs["web"] == paths.web_log_path


def test_read_service_logs_uses_journalctl_for_systemd_user(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(
        "agentx.install.lifecycle.detect_platform",
        lambda: type("Platform", (), {"systemd_user_available": True, "systemd_present_but_unusable": False, "no_systemd": False})(),
    )
    monkeypatch.setattr(
        "agentx.install.lifecycle.subprocess.run",
        lambda args, **kwargs: subprocess.CompletedProcess(args, 0, stdout="journal lines", stderr=""),
    )
    result = read_service_logs(config, "api", tail=25)
    assert result["source"] == "journalctl"
    assert result["unit"] == "agentx-api.service"
    assert result["text"] == "journal lines"


def test_read_service_logs_reads_file_for_non_systemd_mode(tmp_path: Path) -> None:
    config = build_install_config(
        app_root=tmp_path / "app",
        runtime_root=tmp_path / "runtime",
        working_dir=tmp_path / "work",
        profile=InstallProfile.STANDARD,
        model_provider="stub",
        api_host="127.0.0.1",
        api_port=8420,
        web_host="127.0.0.1",
        web_port=5173,
        service_mode=ServiceMode.NONE,
    )
    paths = compute_install_paths(config)
    paths.api_log_path.parent.mkdir(parents=True, exist_ok=True)
    paths.api_log_path.write_text("one\ntwo\nthree\n", encoding="utf-8")
    result = read_service_logs(config, "api", tail=2)
    assert result["source"] == "file"
    assert "two\nthree" in result["text"]


def test_systemd_status_returns_active_and_enabled(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    responses = {
        ("systemctl", "--user", "is-active", "agentx-api.service"): subprocess.CompletedProcess([], 0, stdout="active\n", stderr=""),
        ("systemctl", "--user", "is-enabled", "agentx-api.service"): subprocess.CompletedProcess([], 0, stdout="enabled\n", stderr=""),
        ("systemctl", "--user", "is-active", "agentx-web.service"): subprocess.CompletedProcess([], 3, stdout="inactive\n", stderr=""),
        ("systemctl", "--user", "is-enabled", "agentx-web.service"): subprocess.CompletedProcess([], 0, stdout="enabled\n", stderr=""),
    }
    monkeypatch.setattr(
        "agentx.install.lifecycle.detect_platform",
        lambda: type("Platform", (), {"systemd_user_available": True, "systemd_present_but_unusable": False, "no_systemd": False})(),
    )
    monkeypatch.setattr("agentx.install.lifecycle.subprocess.run", lambda args, **kwargs: responses[tuple(args)])
    result = systemd_status(config)
    assert result["agentx-api.service"]["active"] == "active"
    assert result["agentx-api.service"]["enabled"] == "enabled"
    assert result["agentx-api.service"]["unit_path"].endswith("agentx-api.service")
    assert result["agentx-web.service"]["active"] == "inactive"


def test_status_installation_systemd_fields_include_unit_path_and_journal_source(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr("agentx.install.lifecycle._managed_runtime_report", lambda config, paths: {"required": True, "ready": True, "venv_exists": True, "python_exists": True, "python_path": str(paths.runtime_python_path), "dependencies": []})
    monkeypatch.setattr(
        "agentx.install.lifecycle.systemd_status",
        lambda config: {
            "agentx-api.service": {"active": "active", "enabled": "enabled", "active_ok": True, "enabled_ok": True, "unit_path": str(tmp_path / "units" / "agentx-api.service")},
            "agentx-web.service": {"active": "inactive", "enabled": "enabled", "active_ok": False, "enabled_ok": True, "unit_path": str(tmp_path / "units" / "agentx-web.service")},
        },
    )
    monkeypatch.setattr("agentx.install.lifecycle._http_health", lambda url: "v1/status" in url)
    monkeypatch.setattr("agentx.install.lifecycle._port_open", lambda host, port: port == 8420)
    result = status_installation(config)
    assert result["service_mode"] == "systemd-user"
    assert result["web_url"] == "http://127.0.0.1:5173/"
    assert result["services"]["api"]["systemd_enabled"] == "enabled"
    assert result["services"]["api"]["unit_file_path"].endswith("agentx-api.service")
    assert result["services"]["api"]["log_source"] == "journalctl --user -u agentx-api.service"
    assert result["services"]["api"]["health_url"].endswith("/v1/status")
    assert result["services"]["web"]["web_url"] == "http://127.0.0.1:5173/"


def test_status_installation_direct_mode_uses_file_log_source(tmp_path: Path, monkeypatch) -> None:
    config = build_install_config(
        app_root=tmp_path / "app",
        runtime_root=tmp_path / "runtime",
        working_dir=tmp_path / "work",
        profile=InstallProfile.STANDARD,
        model_provider="stub",
        api_host="127.0.0.1",
        api_port=8420,
        web_host="127.0.0.1",
        web_port=5173,
        service_mode=ServiceMode.NONE,
    )
    monkeypatch.setattr("agentx.install.lifecycle._managed_runtime_report", lambda config, paths: {"required": True, "ready": True, "venv_exists": True, "python_exists": True, "python_path": str(paths.runtime_python_path), "dependencies": []})
    monkeypatch.setattr("agentx.install.lifecycle._cleanup_stale_pid", lambda path: None if path.name == "agentx-web.pid" else 1234)
    monkeypatch.setattr("agentx.install.lifecycle._port_open", lambda host, port: port == 8420)
    monkeypatch.setattr("agentx.install.lifecycle._http_health", lambda url: "v1/status" in url)
    result = status_installation(config)
    assert result["service_mode"] == "none"
    assert result["services"]["api"]["log_source"].endswith("api.log")
    assert result["services"]["api"]["health_url"].endswith("/v1/status")
    assert result["services"]["web"]["web_url"] == "http://127.0.0.1:5173/"
    assert result["services"]["web"]["state"] == "stopped"


def test_cli_parser_includes_service_and_logs_commands() -> None:
    parser = build_parser()
    args = parser.parse_args(["service", "status"])
    assert args.cmd == "service"
    assert args.service_cmd == "status"
    args = parser.parse_args(["logs", "api", "--tail", "20"])
    assert args.cmd == "logs"
    assert args.service == "api"
    assert args.tail == 20
    args = parser.parse_args(["uninstall", "--yes"])
    assert args.cmd == "uninstall"
    assert args.yes is True


def test_cli_service_status_dispatch(tmp_path: Path, monkeypatch, capsys) -> None:
    config = _config(tmp_path)
    install_cfg = tmp_path / "install.json"
    save_install_config(config, install_cfg)
    monkeypatch.setattr(
        "agentx.cli.status_installation",
        lambda install: {
            "service_mode": "systemd-user",
            "app_root": str(config.app_root),
            "runtime_root": str(config.runtime_root),
            "web_url": "http://127.0.0.1:5173/",
            "services": {
                "api": {
                    "state": "active",
                    "systemd_enabled": "enabled",
                    "unit_file_path": str(tmp_path / "units" / "agentx-api.service"),
                    "log_source": "journalctl --user -u agentx-api.service",
                    "health_url": "http://127.0.0.1:8420/v1/status",
                },
                "web": {
                    "state": "inactive",
                    "systemd_enabled": "enabled",
                    "unit_file_path": str(tmp_path / "units" / "agentx-web.service"),
                    "log_source": "journalctl --user -u agentx-web.service",
                    "web_url": "http://127.0.0.1:5173/",
                },
            },
        },
    )
    code = cli_main(["--install-config", str(install_cfg), "service", "status"])
    captured = capsys.readouterr()
    assert code == 0
    assert "Service mode" in captured.out
    assert "Auto-start" in captured.out
    assert "journalctl --user -u agentx-api.service" in captured.out
    assert "agentx-api.service" in captured.out
    assert "agentx logs api --tail 100" in captured.out


def test_autostart_state_from_services_all_enabled() -> None:
    assert autostart_state_from_services(
        {
            "api": {"systemd_enabled": "enabled"},
            "web": {"systemd_enabled": "enabled"},
        }
    ) == "enabled"


def test_autostart_state_from_services_all_disabled() -> None:
    assert autostart_state_from_services(
        {
            "api": {"systemd_enabled": "disabled"},
            "web": {"systemd_enabled": "disabled"},
        }
    ) == "disabled"


def test_autostart_state_from_services_mixed() -> None:
    assert autostart_state_from_services(
        {
            "api": {"systemd_enabled": "enabled"},
            "web": {"systemd_enabled": "disabled"},
        }
    ) == "mixed"


def test_cli_logs_header_for_systemd_user(tmp_path: Path, monkeypatch, capsys) -> None:
    config = _config(tmp_path)
    install_cfg = tmp_path / "install.json"
    save_install_config(config, install_cfg)
    monkeypatch.setattr(
        "agentx.cli.read_service_logs",
        lambda install, service, tail=100: {
            "source": "journalctl",
            "service": service,
            "unit": f"agentx-{service}.service",
            "text": "journal lines",
        },
    )
    code = cli_main(["--install-config", str(install_cfg), "logs", "api", "--tail", "25"])
    captured = capsys.readouterr()
    assert code == 0
    assert "API Logs" in captured.out
    assert "Service: api" in captured.out
    assert "journalctl --user -u agentx-api.service" in captured.out
    assert "Tail: 25" in captured.out
    assert "journal lines" in captured.out


def test_cli_logs_header_for_file_logs(tmp_path: Path, monkeypatch, capsys) -> None:
    config = build_install_config(
        app_root=tmp_path / "app",
        runtime_root=tmp_path / "runtime",
        working_dir=tmp_path / "work",
        profile=InstallProfile.STANDARD,
        model_provider="stub",
        api_host="127.0.0.1",
        api_port=8420,
        web_host="127.0.0.1",
        web_port=5173,
        service_mode=ServiceMode.NONE,
    )
    install_cfg = tmp_path / "install.json"
    save_install_config(config, install_cfg)
    log_path = tmp_path / "runtime" / "logs" / "web.log"
    monkeypatch.setattr(
        "agentx.cli.read_service_logs",
        lambda install, service, tail=100: {
            "source": "file",
            "service": service,
            "path": str(log_path),
            "text": "file lines",
        },
    )
    code = cli_main(["--install-config", str(install_cfg), "logs", "web", "--tail", "40"])
    captured = capsys.readouterr()
    assert code == 0
    assert "WEB Logs" in captured.out or "Web Logs" in captured.out
    assert "Service: web" in captured.out
    assert str(log_path) in captured.out
    assert "Tail: 40" in captured.out
    assert "file lines" in captured.out


def test_cli_stop_dispatch(tmp_path: Path, monkeypatch, capsys) -> None:
    config = _config(tmp_path)
    install_cfg = tmp_path / "install.json"
    save_install_config(config, install_cfg)
    monkeypatch.setattr(
        "agentx.cli.stop_installation",
        lambda install: {
            "api": {"state": "already_stopped"},
            "web": {"state": "disabled"},
        },
    )
    code = cli_main(["--install-config", str(install_cfg), "stop"])
    captured = capsys.readouterr()
    assert code == 0
    assert "Shutdown" in captured.out
    assert "already_stopped" in captured.out


def test_cli_restart_dispatch(tmp_path: Path, monkeypatch, capsys) -> None:
    config = _config(tmp_path)
    install_cfg = tmp_path / "install.json"
    save_install_config(config, install_cfg)
    monkeypatch.setattr(
        "agentx.cli.restart_installation",
        lambda install, install_config_path=None: {
            "ok": True,
            "stop": {"api": {"state": "stopped"}, "web": {"state": "already_stopped"}},
            "start": {
                "profile": config.profile.value,
                "services": {
                    "api": {"state": "started", "detail": "ok", "log_path": str(tmp_path / "api.log")},
                    "web": {"state": "disabled"},
                },
            },
        },
    )
    code = cli_main(["--install-config", str(install_cfg), "restart"])
    captured = capsys.readouterr()
    assert code == 0
    assert "Restart" in captured.out
    assert "started" in captured.out
    assert "stopped" in captured.out


def test_cli_uninstall_dispatch_yes(tmp_path: Path, monkeypatch, capsys) -> None:
    config = _config(tmp_path)
    install_cfg = tmp_path / "install.json"
    save_install_config(config, install_cfg)
    monkeypatch.setattr(
        "agentx.cli.uninstall_installation",
        lambda install, install_config_path=None, remove_app_root=True: {
            "runtime_root": {"state": "removed"},
            "app_root": {"state": "removed" if remove_app_root else "kept"},
            "install_config": {"state": "removed"},
            "bootstrap_record": {"state": "removed"},
            "launchers": {"agentx": {"state": "removed", "path": str(tmp_path / "bin" / "agentx")}},
            "systemd_units": {"state": "removed", "paths": [str(tmp_path / "units" / "agentx-api.service")]},
            "warnings": [],
        },
    )
    code = cli_main(["--install-config", str(install_cfg), "uninstall", "--yes"])
    captured = capsys.readouterr()
    assert code == 0
    assert "Uninstall" in captured.out
    assert "Runtime root: removed" in captured.out
    assert "agentx setup" in captured.out


def test_cli_uninstall_cancelled_without_yes(tmp_path: Path, monkeypatch, capsys) -> None:
    config = _config(tmp_path)
    install_cfg = tmp_path / "install.json"
    save_install_config(config, install_cfg)
    monkeypatch.setattr("builtins.input", lambda prompt="": "n")
    code = cli_main(["--install-config", str(install_cfg), "uninstall"])
    captured = capsys.readouterr()
    assert code == 1
    assert "Uninstall cancelled." in captured.out
