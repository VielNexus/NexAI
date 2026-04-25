from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from agentx_api.app import create_app
from agentx_api.auth import session_store
from agentx_api.config import config
from agentx_api.rag.session import session_tracker
import agentx_api.routes.settings as settings_route


def test_local_mode_allows_protected_routes_without_login(monkeypatch, tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    threads_dir = tmp_path / "threads"
    threads_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "settings_path", settings_path)
    monkeypatch.setattr(config, "threads_dir", threads_dir)
    monkeypatch.setattr(config, "auth_enabled", False)
    with settings_route._CACHE_LOCK:
        settings_route._CACHED_SETTINGS = None
    session_store.reset_for_tests()
    session_tracker.reset_for_tests()

    client = TestClient(create_app())

    status = client.get("/v1/status")
    assert status.status_code == 200, status.text
    assert status.json()["auth_enabled"] is False

    settings = client.get("/v1/settings")
    assert settings.status_code == 200, settings.text

    created = client.post("/v1/threads", json={"title": "Local thread"})
    assert created.status_code == 200, created.text
    thread_id = created.json()["id"]

    threads = client.get("/v1/threads")
    assert threads.status_code == 200, threads.text
    assert [item["id"] for item in threads.json()] == [thread_id]
    session_tracker.reset_for_tests()


def test_login_route_reports_when_auth_is_disabled(monkeypatch, tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    threads_dir = tmp_path / "threads"
    threads_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "settings_path", settings_path)
    monkeypatch.setattr(config, "threads_dir", threads_dir)
    monkeypatch.setattr(config, "auth_enabled", False)
    with settings_route._CACHE_LOCK:
        settings_route._CACHED_SETTINGS = None
    session_store.reset_for_tests()
    session_tracker.reset_for_tests()

    client = TestClient(create_app())
    response = client.post("/v1/auth/login", json={"username": "agentx", "password": "ignored"})

    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "Authentication is disabled for this install."


def test_cors_allows_runtime_web_origin_from_env(monkeypatch) -> None:
    monkeypatch.setenv("AGENTX_CORS_ALLOW_ORIGINS", "http://172.17.24.34:5173")
    client = TestClient(create_app())

    response = client.get("/v1/status", headers={"Origin": "http://172.17.24.34:5173"})

    assert response.status_code == 200, response.text
    assert response.headers["access-control-allow-origin"] == "http://172.17.24.34:5173"


def test_cors_allows_runtime_web_origin_alias_from_env(monkeypatch) -> None:
    monkeypatch.delenv("AGENTX_CORS_ALLOW_ORIGINS", raising=False)
    monkeypatch.setenv("AGENTX_WEB_ORIGIN", "http://172.17.24.34:5173")
    client = TestClient(create_app())

    response = client.get("/v1/status", headers={"Origin": "http://172.17.24.34:5173"})

    assert response.status_code == 200, response.text
    assert response.headers["access-control-allow-origin"] == "http://172.17.24.34:5173"
