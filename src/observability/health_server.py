"""Health Check and Metrics HTTP Server for Project Builder.

Sprint 1: Production Deployment - P1.3 Observability
Provides /health and /metrics endpoints for monitoring and alerting.

Clean Architecture: Adapter layer (infrastructure concern).
SOLID: SRP - Single responsibility for health/metrics HTTP serving.
"""

import json
import logging
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional
import threading

logger = logging.getLogger(__name__)


class HealthMetricsHandler(BaseHTTPRequestHandler):
    """HTTP request handler for health checks and Prometheus metrics.

    Endpoints:
        GET /health - Returns 200 OK with health status JSON
        GET /metrics - Returns Prometheus-formatted metrics
        GET /ready - Returns 200 if service is ready to handle requests
    """

    # Class variable to store application state
    app_state: Dict[str, Any] = {
        'start_time': time.time(),
        'healthy': True,
        'ready': False,
        'version': '1.0.0',
        'metrics': {
            'projects_total': 0,
            'projects_success': 0,
            'projects_failed': 0,
            'tasks_total': 0,
            'tasks_completed': 0,
            'artifacts_total': 0,
            'avg_quality_score': 0.0,
            'total_execution_time_s': 0.0
        }
    }

    def do_GET(self):
        """Handle GET requests for health, metrics, and readiness."""
        if self.path == '/health':
            self._handle_health()
        elif self.path == '/metrics':
            self._handle_metrics()
        elif self.path == '/ready':
            self._handle_ready()
        else:
            self._send_response(404, 'Not Found')

    def _handle_health(self):
        """Return health status as JSON."""
        uptime_s = time.time() - self.app_state['start_time']

        health_data = {
            'status': 'healthy' if self.app_state['healthy'] else 'unhealthy',
            'uptime_seconds': round(uptime_s, 2),
            'version': self.app_state['version'],
            'timestamp': time.time()
        }

        status_code = 200 if self.app_state['healthy'] else 503
        self._send_json_response(status_code, health_data)

    def _handle_ready(self):
        """Return readiness status (whether service can handle requests)."""
        ready_data = {
            'ready': self.app_state['ready'],
            'timestamp': time.time()
        }

        status_code = 200 if self.app_state['ready'] else 503
        self._send_json_response(status_code, ready_data)

    def _handle_metrics(self):
        """Return Prometheus-formatted metrics."""
        metrics = self.app_state['metrics']
        uptime_s = time.time() - self.app_state['start_time']

        # Prometheus text format
        prometheus_metrics = f"""# HELP project_builder_uptime_seconds Service uptime in seconds
# TYPE project_builder_uptime_seconds gauge
project_builder_uptime_seconds {uptime_s:.2f}

# HELP project_builder_projects_total Total number of projects
# TYPE project_builder_projects_total counter
project_builder_projects_total {metrics['projects_total']}

# HELP project_builder_projects_success Number of successful projects
# TYPE project_builder_projects_success counter
project_builder_projects_success {metrics['projects_success']}

# HELP project_builder_projects_failed Number of failed projects
# TYPE project_builder_projects_failed counter
project_builder_projects_failed {metrics['projects_failed']}

# HELP project_builder_tasks_total Total number of tasks
# TYPE project_builder_tasks_total counter
project_builder_tasks_total {metrics['tasks_total']}

# HELP project_builder_tasks_completed Number of completed tasks
# TYPE project_builder_tasks_completed counter
project_builder_tasks_completed {metrics['tasks_completed']}

# HELP project_builder_artifacts_total Total number of artifacts generated
# TYPE project_builder_artifacts_total counter
project_builder_artifacts_total {metrics['artifacts_total']}

# HELP project_builder_quality_score_avg Average quality score of artifacts
# TYPE project_builder_quality_score_avg gauge
project_builder_quality_score_avg {metrics['avg_quality_score']:.2f}

# HELP project_builder_execution_time_seconds_total Total execution time
# TYPE project_builder_execution_time_seconds_total counter
project_builder_execution_time_seconds_total {metrics['total_execution_time_s']:.2f}
"""

        self._send_response(200, prometheus_metrics, content_type='text/plain; version=0.0.4')

    def _send_json_response(self, status_code: int, data: Dict[str, Any]):
        """Send JSON response."""
        self._send_response(status_code, json.dumps(data), content_type='application/json')

    def _send_response(self, status_code: int, body: str, content_type: str = 'text/plain'):
        """Send HTTP response."""
        self.send_response(status_code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body.encode('utf-8'))

    def log_message(self, format, *args):
        """Override to use Python logging instead of stderr."""
        logger.debug(f"{self.address_string()} - {format % args}")


class HealthServer:
    """Health check and metrics server (runs in background thread).

    Example:
        server = HealthServer(port=8000)
        server.start()

        # Update metrics
        HealthMetricsHandler.app_state['metrics']['projects_total'] += 1
        HealthMetricsHandler.app_state['ready'] = True

        # Shutdown
        server.stop()
    """

    def __init__(self, host: str = '0.0.0.0', port: int = 8000):
        """Initialize health server.

        Args:
            host: Bind address (default: 0.0.0.0 for all interfaces)
            port: Port to listen on (default: 8000)
        """
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        """Start server in background thread."""
        self.server = HTTPServer((self.host, self.port), HealthMetricsHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        logger.info(f"Health server started on http://{self.host}:{self.port}")
        logger.info(f"  Health check: http://{self.host}:{self.port}/health")
        logger.info(f"  Metrics: http://{self.host}:{self.port}/metrics")
        logger.info(f"  Readiness: http://{self.host}:{self.port}/ready")

    def stop(self):
        """Stop server gracefully."""
        if self.server:
            logger.info("Shutting down health server...")
            self.server.shutdown()
            self.server.server_close()
            if self.thread:
                self.thread.join(timeout=5)
            logger.info("Health server stopped")

    @staticmethod
    def update_metrics(metrics: Dict[str, Any]):
        """Update application metrics (thread-safe update).

        Args:
            metrics: Dict with metric updates (partial or full)
        """
        HealthMetricsHandler.app_state['metrics'].update(metrics)

    @staticmethod
    def set_ready(ready: bool = True):
        """Set service readiness state.

        Args:
            ready: Whether service is ready to handle requests
        """
        HealthMetricsHandler.app_state['ready'] = ready

    @staticmethod
    def set_healthy(healthy: bool = True):
        """Set service health state.

        Args:
            healthy: Whether service is healthy
        """
        HealthMetricsHandler.app_state['healthy'] = healthy
