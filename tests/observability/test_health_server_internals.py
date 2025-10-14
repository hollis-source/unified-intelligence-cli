import os
import stat
import json
import types
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from src.observability.health_server import HealthServer, HealthMetricsHandler


@pytest.fixture
def started_server_ephemeral():
    server = HealthServer(host="127.0.0.1", port=0)
    server.start()
    port = server.server.server_address[1]
    try:
        yield server, port
    finally:
        server.stop()


def test_aggregate_status_empty_returns_down():
    assert HealthMetricsHandler._aggregate_status(HealthMetricsHandler, []) == "down"


def test_unknown_endpoint_returns_404(started_server_ephemeral):
    _server, port = started_server_ephemeral
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/does-not-exist", timeout=2)
    assert exc.value.code == 404


@pytest.mark.parametrize(
    "status_code, expected_ok",
    [(200, True), (500, False)],
)
def test_check_surrealdb_handles_http_status(monkeypatch, status_code, expected_ok):
    class Resp:
        def __init__(self, status):
            self.status = status
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
    def fake_urlopen(req, timeout=0.3):
        return Resp(status_code)
    monkeypatch.setenv("SURREALDB_URL", "http://localhost:9999")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    result = HealthMetricsHandler._check_surrealdb(HealthMetricsHandler)
    assert result["name"] == "db"
    assert result["ok"] is expected_ok


def test_check_surrealdb_handles_exception(monkeypatch):
    def fake_urlopen(req, timeout=0.3):
        raise TimeoutError("boom")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    res = HealthMetricsHandler._check_surrealdb(HealthMetricsHandler)
    assert res["name"] == "db" and res["ok"] is False
    assert "reason" in res


def test_check_redis_uses_explicit_url_when_set(monkeypatch):
    # Provide fake redis module
    fake_redis = types.SimpleNamespace()
    captured = {}
    class FakeClient:
        def ping(self):
            return True
    def from_url(url, socket_timeout=0.3, socket_connect_timeout=0.3):
        captured["url"] = url
        return FakeClient()
    fake_redis.from_url = from_url

    monkeypatch.setenv("REDIS_URL", "redis://:pw@host:1234/0")
    monkeypatch.delenv("REDIS_HOST", raising=False)
    monkeypatch.setitem(__import__("sys").modules, "redis", fake_redis)

    res = HealthMetricsHandler._check_redis(HealthMetricsHandler)
    assert res == {"name": "cache", "ok": True}
    assert captured["url"].startswith("redis://")


def test_check_redis_builds_url_from_components_with_password_file(tmp_path, monkeypatch):
    pw_file = tmp_path / "pw.txt"
    pw_file.write_text("pa:ss@word\n", encoding="utf-8")

    fake_redis = types.SimpleNamespace()
    captured = {}
    class FakeClient:
        def ping(self):
            return True
    def from_url(url, socket_timeout=0.3, socket_connect_timeout=0.3):
        captured["url"] = url
        return FakeClient()
    fake_redis.from_url = from_url

    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("REDIS_HOST", "example.com")
    monkeypatch.setenv("REDIS_PORT", "6380")
    monkeypatch.setenv("REDIS_PASSWORD_FILE", str(pw_file))
    monkeypatch.setitem(__import__("sys").modules, "redis", fake_redis)

    res = HealthMetricsHandler._check_redis(HealthMetricsHandler)
    assert res == {"name": "cache", "ok": True}
    # Ensure password got URL-encoded
    assert "@" in captured["url"]  # host separator
    assert "%40" in captured["url"]  # encoded @ from password


def test_check_redis_failure_returns_reason(monkeypatch):
    # Fake redis that always fails
    class FakeClient:
        def ping(self):
            raise ConnectionError("nope")
    def from_url(url, socket_timeout=0.3, socket_connect_timeout=0.3):
        return FakeClient()
    fake_redis = types.SimpleNamespace(from_url=from_url)

    monkeypatch.setitem(__import__("sys").modules, "redis", fake_redis)
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")

    res = HealthMetricsHandler._check_redis(HealthMetricsHandler)
    assert res["name"] == "cache"
    assert res["ok"] is False
    assert "reason" in res


def test_check_ssh_missing_file(monkeypatch, tmp_path):
    monkeypatch.setenv("PB_SSH_KEY_PATH", str(tmp_path / "nope"))
    res = HealthMetricsHandler._check_ssh(HealthMetricsHandler)
    assert res == {"name": "ssh", "ok": False, "reason": "key_not_found"}


def test_check_ssh_insecure_permissions(tmp_path, monkeypatch):
    key = tmp_path / "id_ed25519"
    key.write_text("secret")
    # Bad perms 644
    key.chmod(0o644)
    monkeypatch.setenv("PB_SSH_KEY_PATH", str(key))
    res = HealthMetricsHandler._check_ssh(HealthMetricsHandler)
    assert res["name"] == "ssh" and res["ok"] is False
    assert res["reason"].startswith("insecure_perms_")


def test_check_ssh_ok_permissions(tmp_path, monkeypatch):
    key = tmp_path / "id_ed25519"
    key.write_text("secret")
    key.chmod(0o600)
    monkeypatch.setenv("PB_SSH_KEY_PATH", str(key))
    res = HealthMetricsHandler._check_ssh(HealthMetricsHandler)
    assert res == {"name": "ssh", "ok": True}

