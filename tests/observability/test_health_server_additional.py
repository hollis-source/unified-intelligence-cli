import json
import urllib.request
from typing import Dict, Any, List

import pytest

from src.observability.health_server import HealthServer, HealthMetricsHandler


@pytest.fixture
def started_server():
    server = HealthServer(host="127.0.0.1", port=0)
    server.start()
    port = server.server.server_address[1]
    try:
        yield server, port
    finally:
        server.stop()


def http_get_json(url: str, timeout: float = 2.0) -> Dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        assert resp.getheader("Content-Type").startswith("application/json")
        return json.loads(resp.read().decode()), resp.getcode()


def http_get_text(url: str, timeout: float = 2.0):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read().decode(), resp.getcode(), resp.getheader("Content-Type")


@pytest.mark.parametrize(
    "services, expected_status, expected_code",
    [
        ([{"name": "db", "ok": True}, {"name": "cache", "ok": True}, {"name": "ssh", "ok": True}], "ok", 200),
        ([{"name": "db", "ok": True}, {"name": "cache", "ok": False}], "degraded", 200),
        ([{"name": "db", "ok": False}, {"name": "cache", "ok": True}], "down", 503),
    ],
)
def test_health_content_type_and_codes(monkeypatch, started_server, services: List[Dict[str, Any]], expected_status: str, expected_code: int):
    _server, port = started_server

    def fake_check_services(self, timeout_ms: int = 800):
        return services

    monkeypatch.setattr(HealthMetricsHandler, "_check_services", fake_check_services, raising=True)

    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as resp:
            body = json.loads(resp.read().decode())
            assert resp.getcode() == expected_code
            assert resp.getheader("Content-Type").startswith("application/json")
            assert body["status"] == expected_status
    except Exception as e:
        if expected_code == 503 and hasattr(e, "code") and e.code == 503:
            body = json.loads(e.read().decode())
            assert body["status"] == expected_status
        else:
            raise


def test_unknown_path_404_plain_text(started_server):
    _server, port = started_server
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/nope", timeout=2)
        pytest.fail("Expected HTTPError for 404")
    except Exception as e:
        assert hasattr(e, "code") and e.code == 404


def test_metrics_reflect_updates_and_content_type(started_server):
    _server, port = started_server

    HealthServer.update_metrics({
        "projects_total": 5,
        "projects_success": 3,
        "projects_failed": 2,
        "tasks_total": 7,
        "tasks_completed": 4,
        "artifacts_total": 9,
        "avg_quality_score": 1.23,
        "total_execution_time_s": 12.34,
    })

    text, status, content_type = http_get_text(f"http://127.0.0.1:{port}/metrics")
    assert status == 200
    assert content_type.startswith("text/plain")
    assert "project_builder_projects_total 5" in text
    assert "project_builder_projects_success 3" in text
    assert "project_builder_projects_failed 2" in text
    assert "project_builder_tasks_total 7" in text
    assert "project_builder_tasks_completed 4" in text
    assert "project_builder_artifacts_total 9" in text
    assert "project_builder_quality_score_avg 1.23" in text
    assert "project_builder_execution_time_seconds_total 12.34" in text


def test_ready_content_type_and_toggle(started_server):
    server, port = started_server

    # Initially 503
    with pytest.raises(Exception):
        urllib.request.urlopen(f"http://127.0.0.1:{port}/ready", timeout=2)

    server.set_ready(True)
    (body, code) = http_get_json(f"http://127.0.0.1:{port}/ready")
    assert code == 200 and body["ready"] is True

    server.set_ready(False)
    with pytest.raises(Exception):
        urllib.request.urlopen(f"http://127.0.0.1:{port}/ready", timeout=2)


def test_health_empty_services_is_down(monkeypatch, started_server):
    _server, port = started_server

    def fake_check_services(self, timeout_ms: int = 800):
        return []

    monkeypatch.setattr(HealthMetricsHandler, "_check_services", fake_check_services, raising=True)

    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
        pytest.fail("Expected 503 for empty services")
    except Exception as e:
        assert hasattr(e, "code") and e.code == 503

