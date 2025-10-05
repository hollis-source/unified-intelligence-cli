"""Metrics Dashboard HTTP Server for PriorityWorker

Exposes metrics via HTTP endpoints on port 8080.
Clean Architecture: Adapter layer (external interface)
SOLID: SRP (metrics exposure only), ISP (minimal interface)

Generated from ULTRATHINK design on 2025-10-04.
"""

import asyncio
import json
import os
import psutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
from aiohttp import web


class MetricsDashboard:
    """HTTP server for exposing PriorityWorker metrics.

    Runs in background asyncio task, non-blocking to main daemon.
    Serves endpoints for health, metrics, status, and Prometheus format.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize dashboard with configuration.

        Args:
            config: Dashboard configuration
                - port: HTTP server port (default 8080)
                - host: Bind address (default localhost)
                - metrics_dir: Path to metrics JSON files
                - pid_file: Path to PID file for process stats
        """
        self.port = config.get('port', 8080)
        self.host = config.get('host', 'localhost')
        self.metrics_dir = Path(config.get('metrics_dir', 'data/metrics'))
        self.pid_file = Path(config.get('pid_file', '/tmp/priority_worker_production.pid'))
        self.start_time = time.time()
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None

        # Setup routes
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/metrics', self.handle_metrics)
        self.app.router.add_get('/status', self.handle_status)
        self.app.router.add_get('/metrics/prometheus', self.handle_prometheus)
        self.app.router.add_get('/', self.handle_root)

    async def start(self):
        """Start HTTP server in background."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()
        print(f"Metrics dashboard started on http://{self.host}:{self.port}")

    async def stop(self):
        """Stop HTTP server gracefully."""
        if self.runner:
            await self.runner.cleanup()

    async def handle_health(self, request: web.Request) -> web.Response:
        """GET /health - Process health status.

        Returns 200 OK if dashboard is responding (Docker health check).
        Includes detailed process info if PID file is available.
        """
        try:
            # Basic health: Dashboard is up and responding
            dashboard_uptime = time.time() - self.start_time
            health = {
                'status': 'healthy',
                'dashboard_uptime_seconds': int(dashboard_uptime),
                'dashboard_uptime_human': str(timedelta(seconds=int(dashboard_uptime))),
                'timestamp': datetime.utcnow().isoformat()
            }

            # Enhanced metrics if PID file available (optional)
            pid = self._get_pid()
            if pid is not None:
                try:
                    process = psutil.Process(pid)
                    uptime = time.time() - process.create_time()
                    memory_mb = process.memory_info().rss / 1024 / 1024

                    health.update({
                        'pid': pid,
                        'process_uptime_seconds': int(uptime),
                        'process_uptime_human': str(timedelta(seconds=int(uptime))),
                        'memory_mb': round(memory_mb, 2),
                        'cpu_percent': process.cpu_percent(interval=0.1)
                    })
                except psutil.NoSuchProcess:
                    health['pid_warning'] = 'PID file exists but process not found'

            return web.json_response(health)

        except Exception as e:
            # Still return 200 for basic health (dashboard is up)
            # but include error details for debugging
            return web.json_response({
                'status': 'healthy',
                'warning': f'Health check error: {str(e)}',
                'timestamp': datetime.utcnow().isoformat()
            })

    async def handle_metrics(self, request: web.Request) -> web.Response:
        """GET /metrics - Task execution metrics."""
        try:
            # Find most recent metrics file
            metrics_files = sorted(self.metrics_dir.glob('priority_worker_*.json'), reverse=True)
            if not metrics_files:
                return web.json_response({
                    'error': 'No metrics available'
                }, status=404)

            latest_file = metrics_files[0]
            with open(latest_file, 'r') as f:
                metrics_data = json.load(f)

            # Calculate aggregated metrics
            total_tasks = metrics_data.get('total_tasks_processed', 0)
            successful_tasks = metrics_data.get('successful_tasks', 0)
            failed_tasks = metrics_data.get('failed_tasks', 0)
            total_time = metrics_data.get('total_execution_time', 0)

            success_rate = (successful_tasks / total_tasks * 100) if total_tasks > 0 else 0
            avg_latency = (total_time / total_tasks) if total_tasks > 0 else 0

            metrics = {
                'total_tasks': total_tasks,
                'successful_tasks': successful_tasks,
                'failed_tasks': failed_tasks,
                'success_rate_percent': round(success_rate, 2),
                'average_latency_seconds': round(avg_latency, 3),
                'total_execution_time': round(total_time, 2),
                'last_updated': metrics_data.get('timestamp', 'unknown'),
                'metrics_file': latest_file.name
            }

            return web.json_response(metrics)

        except Exception as e:
            return web.json_response({
                'error': str(e)
            }, status=500)

    async def handle_status(self, request: web.Request) -> web.Response:
        """GET /status - Current daemon status."""
        try:
            # Read cycle state from metrics
            metrics_files = sorted(self.metrics_dir.glob('priority_worker_*.json'), reverse=True)
            cycle_info = {}

            if metrics_files:
                with open(metrics_files[0], 'r') as f:
                    data = json.load(f)
                    cycle_info = {
                        'last_cycle': data.get('timestamp', 'unknown'),
                        'tasks_in_last_cycle': data.get('total_tasks_processed', 0),
                        'last_cycle_duration': data.get('total_execution_time', 0)
                    }

            pid = self._get_pid()
            process_running = False
            if pid:
                try:
                    psutil.Process(pid)
                    process_running = True
                except psutil.NoSuchProcess:
                    pass

            status = {
                'daemon_running': process_running,
                'dashboard_uptime_seconds': int(time.time() - self.start_time),
                **cycle_info,
                'timestamp': datetime.utcnow().isoformat()
            }

            return web.json_response(status)

        except Exception as e:
            return web.json_response({
                'error': str(e)
            }, status=500)

    async def handle_prometheus(self, request: web.Request) -> web.Response:
        """GET /metrics/prometheus - Prometheus-compatible format."""
        try:
            # Find most recent metrics
            metrics_files = sorted(self.metrics_dir.glob('priority_worker_*.json'), reverse=True)
            if not metrics_files:
                return web.Response(text='# No metrics available\n', content_type='text/plain')

            with open(metrics_files[0], 'r') as f:
                data = json.load(f)

            total_tasks = data.get('total_tasks_processed', 0)
            successful_tasks = data.get('successful_tasks', 0)
            failed_tasks = data.get('failed_tasks', 0)
            success_rate = (successful_tasks / total_tasks) if total_tasks > 0 else 0

            # Prometheus exposition format
            prom_metrics = f"""# HELP priority_worker_tasks_total Total tasks processed
# TYPE priority_worker_tasks_total counter
priority_worker_tasks_total {total_tasks}

# HELP priority_worker_tasks_successful Successful tasks
# TYPE priority_worker_tasks_successful counter
priority_worker_tasks_successful {successful_tasks}

# HELP priority_worker_tasks_failed Failed tasks
# TYPE priority_worker_tasks_failed counter
priority_worker_tasks_failed {failed_tasks}

# HELP priority_worker_success_rate Task success rate (0-1)
# TYPE priority_worker_success_rate gauge
priority_worker_success_rate {success_rate:.4f}

# HELP priority_worker_execution_time_seconds Total execution time
# TYPE priority_worker_execution_time_seconds counter
priority_worker_execution_time_seconds {data.get('total_execution_time', 0):.2f}
"""

            # Add process metrics if available
            pid = self._get_pid()
            if pid:
                try:
                    process = psutil.Process(pid)
                    memory_bytes = process.memory_info().rss
                    cpu_percent = process.cpu_percent(interval=0.1)

                    prom_metrics += f"""
# HELP priority_worker_memory_bytes Process memory usage
# TYPE priority_worker_memory_bytes gauge
priority_worker_memory_bytes {memory_bytes}

# HELP priority_worker_cpu_percent Process CPU usage percentage
# TYPE priority_worker_cpu_percent gauge
priority_worker_cpu_percent {cpu_percent}
"""
                except psutil.NoSuchProcess:
                    pass

            return web.Response(text=prom_metrics, content_type='text/plain; version=0.0.4')

        except Exception as e:
            return web.Response(text=f'# Error: {e}\n', content_type='text/plain', status=500)

    async def handle_root(self, request: web.Request) -> web.Response:
        """GET / - Simple HTML dashboard."""
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>PriorityWorker Metrics Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: monospace; margin: 20px; background: #1e1e1e; color: #d4d4d4; }
        h1 { color: #4ec9b0; }
        .endpoint { margin: 10px 0; padding: 10px; background: #252526; border-left: 3px solid #007acc; }
        a { color: #569cd6; text-decoration: none; }
        a:hover { text-decoration: underline; }
        code { background: #1e1e1e; padding: 2px 6px; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>PriorityWorker Metrics Dashboard</h1>
    <p>Autonomous Task Execution Daemon - Production Monitoring</p>

    <h2>Available Endpoints:</h2>

    <div class="endpoint">
        <strong><a href="/health">GET /health</a></strong><br>
        Process health status (PID, uptime, memory, CPU)
    </div>

    <div class="endpoint">
        <strong><a href="/metrics">GET /metrics</a></strong><br>
        Task execution metrics (success rate, latency, throughput)
    </div>

    <div class="endpoint">
        <strong><a href="/status">GET /status</a></strong><br>
        Current daemon status (cycle state, last execution)
    </div>

    <div class="endpoint">
        <strong><a href="/metrics/prometheus">GET /metrics/prometheus</a></strong><br>
        Prometheus-compatible metrics format
    </div>

    <h2>Quick Links:</h2>
    <ul>
        <li><a href="/health">Health Check</a></li>
        <li><a href="/metrics">View Metrics</a></li>
        <li><a href="/status">Daemon Status</a></li>
    </ul>

    <hr>
    <p><small>Generated by unified-intelligence-cli | Clean Architecture | SOLID Principles</small></p>
</body>
</html>
"""
        return web.Response(text=html, content_type='text/html')

    def _get_pid(self) -> Optional[int]:
        """Read PID from PID file."""
        try:
            if self.pid_file.exists():
                return int(self.pid_file.read_text().strip())
        except (ValueError, IOError):
            pass
        return None
