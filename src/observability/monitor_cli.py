from __future__ import annotations

import time
import click

from src.observability.health_server import HealthServer


@click.command()
@click.option("--host", default="127.0.0.1", help="Host to bind health server")
@click.option("--port", default=0, type=int, help="Port to bind (0 for ephemeral)")
@click.option("--duration", default=1.0, type=float, help="Run duration in seconds (for tests)")
def monitor(host: str, port: int, duration: float) -> None:
    """Start a health server briefly to monitor and then stop (test-friendly)."""
    server = HealthServer(host=host, port=port)
    server.start()
    bound_port = server.server.server_address[1]  # type: ignore[union-attr]
    click.echo(f"Health server started at http://{host}:{bound_port}")
    server.set_ready(True)
    time.sleep(max(0.0, duration))
    server.stop()
    click.echo("Health server stopped")


if __name__ == "__main__":
    monitor()

