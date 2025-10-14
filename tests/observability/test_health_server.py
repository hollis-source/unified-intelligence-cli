import json
import time
import urllib.request
from typing import List, Dict, Any

import pytest

from src.observability.health_server import HealthServer, HealthMetricsHandler


@pytest.fixture
def started_server():
    """Start HealthServer on an ephemeral port and ensure cleanup."""
    server = HealthServer(host="127.0.0.1", port=0)
    server.start()
    # Discover ephemeral port assigned
    bound_port = server.server.server_address[1]
    try:
        yield server, bound_port
    finally:
        server.stop()


def http_get_json(url: str, timeout: float = 2.0) -> Dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        assert resp.getheader("Content-Type").startswith("application/json")
        return json.loads(resp.read().decode())


def http_get_text(url: str, timeout: float = 2.0) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read().decode(), resp.getcode(), resp.getheader("Content-Type")


def test_ready_endpoint_transitions(started_server):
    server, port = started_server

    # Initially not ready => 503
    with pytest.raises(Exception):
        urllib.request.urlopen(f"http://127.0.0.1:{port}/ready", timeout=2)

    # Mark ready and verify 200
    server.set_ready(True)
    data = http_get_json(f"http://127.0.0.1:{port}/ready")
    assert data["ready"] is True
    assert isinstance(data["timestamp"], float)


def test_metrics_endpoint_prometheus_format(started_server):
    _server, port = started_server

    text, status, content_type = http_get_text(f"http://127.0.0.1:{port}/metrics")
    assert status == 200
    assert "# HELP project_builder_uptime_seconds" in text
    assert "# TYPE project_builder_uptime_seconds gauge" in text
    assert content_type.startswith("text/plain")


@pytest.mark.parametrize(
    "services, expected_status, expected_code",
    [
        ([{"name": "db", "ok": True}, {"name": "cache", "ok": True}, {"name": "ssh", "ok": True}], "ok", 200),
        ([{"name": "db", "ok": True}, {"name": "cache", "ok": False}], "degraded", 200),
        ([{"name": "db", "ok": False}, {"name": "cache", "ok": True}], "down", 503),
    ],
)
def test_health_status_aggregation(monkeypatch, started_server, services: List[Dict[str, Any]], expected_status: str, expected_code: int):
    _server, port = started_server

    # Monkeypatch dependency checks to deterministic results
    def fake_check_services(self, timeout_ms: int = 800):
        return services

    monkeypatch.setattr(HealthMetricsHandler, "_check_services", fake_check_services, raising=True)

    # Request /health
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as resp:
            body = json.loads(resp.read().decode())
            assert resp.getcode() == expected_code
            assert body["status"] == expected_status
            assert "uptime_seconds" in body
            assert "version" in body
            assert isinstance(body["timestamp"], float)
    except Exception as e:
        # For expected_code == 503, urllib raises on HTTPError; handle and assert
        if expected_code == 503 and hasattr(e, "code") and e.code == 503:
            body = json.loads(e.read().decode())
            assert body["status"] == expected_status
        else:
            raise


def test_health_includes_services_payload(monkeypatch, started_server):
    _server, port = started_server

    services = [
        {"name": "db", "ok": True},
        {"name": "cache", "ok": False, "reason": "timeout"},
        {"name": "ssh", "ok": True},
    ]

    def fake_check_services(self, timeout_ms: int = 800):
        return services

    monkeypatch.setattr(HealthMetricsHandler, "_check_services", fake_check_services, raising=True)

    body = http_get_json(f"http://127.0.0.1:{port}/health")
    assert body["status"] == "degraded"
    assert body["services"] == services
    assert isinstance(body["uptime_seconds"], float)

