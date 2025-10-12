import os
import json
import asyncio
import time
from pathlib import Path

from datetime import datetime

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer, TestClient

from src.priority_queue.adapters.metrics_dashboard import MetricsDashboard


@pytest.mark.asyncio
async def test_health_basic(tmp_path: Path):
    dashboard = MetricsDashboard({
        "metrics_dir": str(tmp_path / "metrics"),
        "pid_file": str(tmp_path / "priority_worker.pid"),
        "host": "127.0.0.1",
        "port": 0,
    })

    async with TestServer(dashboard.app) as server:
        async with TestClient(server) as client:
            resp = await client.get("/health")
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "healthy"
            assert isinstance(data["dashboard_uptime_seconds"], int)
            assert "timestamp" in data
            assert "pid" not in data  # no pid file provided


@pytest.mark.asyncio
async def test_health_with_pid(tmp_path: Path):
    pid_file = tmp_path / "priority_worker.pid"
    pid_file.write_text(str(os.getpid()))

    dashboard = MetricsDashboard({
        "metrics_dir": str(tmp_path / "metrics"),
        "pid_file": str(pid_file),
        "host": "127.0.0.1",
        "port": 0,
    })

    async with TestServer(dashboard.app) as server:
        async with TestClient(server) as client:
            resp = await client.get("/health")
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "healthy"
            assert data["pid"] == os.getpid()
            assert "memory_mb" in data
            assert "cpu_percent" in data


@pytest.mark.asyncio
async def test_metrics_404_when_no_files(tmp_path: Path):
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    dashboard = MetricsDashboard({
        "metrics_dir": str(metrics_dir),
        "pid_file": str(tmp_path / "priority_worker.pid"),
        "host": "127.0.0.1",
        "port": 0,
    })

    async with TestServer(dashboard.app) as server:
        async with TestClient(server) as client:
            resp = await client.get("/metrics")
            assert resp.status == 404
            data = await resp.json()
            assert data["error"] == "No metrics available"


@pytest.mark.asyncio
async def test_metrics_returns_aggregates(tmp_path: Path):
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "total_tasks_processed": 10,
        "successful_tasks": 7,
        "failed_tasks": 3,
        "total_execution_time": 5.0,
        "timestamp": "2025-10-11T00:00:00Z",
    }
    metrics_path = metrics_dir / "priority_worker_test.json"
    metrics_path.write_text(json.dumps(payload))

    dashboard = MetricsDashboard({
        "metrics_dir": str(metrics_dir),
        "pid_file": str(tmp_path / "priority_worker.pid"),
        "host": "127.0.0.1",
        "port": 0,
    })

    async with TestServer(dashboard.app) as server:
        async with TestClient(server) as client:
            resp = await client.get("/metrics")
            assert resp.status == 200
            data = await resp.json()
            assert data["total_tasks"] == 10
            assert data["successful_tasks"] == 7
            assert data["failed_tasks"] == 3
            assert data["success_rate_percent"] == 70.0
            assert data["average_latency_seconds"] == 0.5
            assert data["total_execution_time"] == 5.0
            assert data["metrics_file"] == metrics_path.name


@pytest.mark.asyncio
async def test_status_daemon_running_flags(tmp_path: Path):
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    # Write a simple metrics file so status includes cycle info
    (metrics_dir / "priority_worker_latest.json").write_text(json.dumps({
        "timestamp": "2025-10-11T01:02:03Z",
        "total_tasks_processed": 2,
        "total_execution_time": 0.25,
    }))

    # Case 1: No PID file
    dashboard1 = MetricsDashboard({
        "metrics_dir": str(metrics_dir),
        "pid_file": str(tmp_path / "missing.pid"),
        "host": "127.0.0.1",
        "port": 0,
    })
    async with TestServer(dashboard1.app) as server1:
        async with TestClient(server1) as client1:
            resp1 = await client1.get("/status")
            assert resp1.status == 200
            data1 = await resp1.json()
            assert data1["daemon_running"] is False
            assert data1["tasks_in_last_cycle"] == 2
            assert data1["last_cycle_duration"] == 0.25

    # Case 2: Valid PID file
    pid_file = tmp_path / "priority_worker.pid"
    pid_file.write_text(str(os.getpid()))
    dashboard2 = MetricsDashboard({
        "metrics_dir": str(metrics_dir),
        "pid_file": str(pid_file),
        "host": "127.0.0.1",
        "port": 0,
    })
    async with TestServer(dashboard2.app) as server2:
        async with TestClient(server2) as client2:
            resp2 = await client2.get("/status")
            assert resp2.status == 200
            data2 = await resp2.json()
            assert data2["daemon_running"] is True


@pytest.mark.asyncio
async def test_prometheus_no_metrics(tmp_path: Path):
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    dashboard = MetricsDashboard({
        "metrics_dir": str(metrics_dir),
        "pid_file": str(tmp_path / "priority_worker.pid"),
        "host": "127.0.0.1",
        "port": 0,
    })

    async with TestServer(dashboard.app) as server:
        async with TestClient(server) as client:
            resp = await client.get("/metrics/prometheus")
            assert resp.status == 200
            text = await resp.text()
            assert "# No metrics available" in text
            assert resp.headers["Content-Type"].startswith("text/plain")


@pytest.mark.asyncio
async def test_prometheus_with_metrics(tmp_path: Path):
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "total_tasks_processed": 10,
        "successful_tasks": 7,
        "failed_tasks": 3,
        "total_execution_time": 5.0,
        "timestamp": "2025-10-11T00:00:00Z",
    }
    (metrics_dir / "priority_worker_latest.json").write_text(json.dumps(payload))

    dashboard = MetricsDashboard({
        "metrics_dir": str(metrics_dir),
        "pid_file": str(tmp_path / "priority_worker.pid"),
        "host": "127.0.0.1",
        "port": 0,
    })

    async with TestServer(dashboard.app) as server:
        async with TestClient(server) as client:
            resp = await client.get("/metrics/prometheus")
            assert resp.status == 200
            text = await resp.text()
            assert "priority_worker_tasks_total 10" in text
            assert "priority_worker_tasks_successful 7" in text
            assert "priority_worker_tasks_failed 3" in text
            assert "priority_worker_success_rate 0.7000" in text
            assert "priority_worker_execution_time_seconds 5.00" in text
            assert resp.headers["Content-Type"].startswith("text/plain")


@pytest.mark.asyncio
async def test_root_returns_html(tmp_path: Path):
    dashboard = MetricsDashboard({
        "metrics_dir": str(tmp_path / "metrics"),
        "pid_file": str(tmp_path / "priority_worker.pid"),
        "host": "127.0.0.1",
        "port": 0,
    })

    async with TestServer(dashboard.app) as server:
        async with TestClient(server) as client:
            resp = await client.get("/")
            assert resp.status == 200
            text = await resp.text()
            assert "PriorityWorker Metrics Dashboard" in text




@pytest.mark.asyncio
async def test_staleness_endpoint(tmp_path: Path):
    metrics_dir = tmp_path / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    # Case 1: No metrics -> 404
    dashboard1 = MetricsDashboard({
        "metrics_dir": str(metrics_dir),
        "pid_file": str(tmp_path / "priority_worker.pid"),
        "host": "127.0.0.1",
        "port": 0,
    })
    async with TestServer(dashboard1.app) as server1:
        async with TestClient(server1) as client1:
            resp1 = await client1.get("/metrics/staleness")
            assert resp1.status == 404

    # Case 2: Recent metrics -> not stale
    payload = {
        "total_tasks_processed": 1,
        "successful_tasks": 1,
        "failed_tasks": 0,
        "total_execution_time": 0.1,
        "timestamp": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    }
    metrics_file = metrics_dir / "priority_worker_latest.json"
    metrics_file.write_text(json.dumps(payload))

    dashboard2 = MetricsDashboard({
        "metrics_dir": str(metrics_dir),
        "pid_file": str(tmp_path / "priority_worker.pid"),
        "host": "127.0.0.1",
        "port": 0,
    })
    async with TestServer(dashboard2.app) as server2:
        async with TestClient(server2) as client2:
            resp2 = await client2.get("/metrics/staleness?max_age=300")
            assert resp2.status == 200
            data = await resp2.json()
            assert data["stale"] is False
            assert "age_seconds" in data and isinstance(data["age_seconds"], int)
            assert data["metrics_file"] == metrics_file.name
