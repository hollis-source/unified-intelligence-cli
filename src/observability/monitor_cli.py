"""Simple monitoring CLI to run the HealthServer for a short duration.

Clean Architecture: adapter/CLI to start observability server without
impacting core orchestration. Depends only on HealthServer abstraction.
"""
from __future__ import annotations

import time
import click
from typing import Optional

from .health_server import HealthServer, HealthMetricsHandler


@click.command(help="Start health/metrics server for monitoring")
@click.option("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
@click.option("--port", default=8000, type=int, help="Port (0 for ephemeral)")
@click.option("--duration", default=5.0, type=float, help="Run seconds before stopping")
@click.option("--ready/--not-ready", default=True, help="Set readiness flag on start")
def monitor(host: str, port: int, duration: float, ready: bool) -> None:
    """Start the health server briefly for monitoring/smoke checks."""
    server = HealthServer(host=host, port=port)
    try:
        server.start()
    except OSError as e:
        # If address in use, retry with ephemeral port 0 to avoid flaky failures
        if getattr(e, 'errno', None) == 98 or 'Address already in use' in str(e):
            server = HealthServer(host=host, port=0)
            server.start()
        else:
            raise

    # discover bound port if ephemeral
    bound_port: int = server.server.server_address[1] if server.server else port

    # set readiness and print endpoints
    HealthMetricsHandler.app_state["ready"] = ready
    click.echo(f"Health server started on http://{host}:{bound_port}")
    click.echo(f"  Health:   http://{host}:{bound_port}/health")
    click.echo(f"  Metrics:  http://{host}:{bound_port}/metrics")
    click.echo(f"  Readiness:http://{host}:{bound_port}/ready")

    # run for requested duration then stop
    time.sleep(max(0.0, duration))
    server.stop()
    click.echo("Health server stopped")

