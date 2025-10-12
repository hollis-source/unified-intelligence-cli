#!/usr/bin/env python3
"""Production entrypoint for Project Builder health server.

Sprint 1: Production Deployment - P1.3
Starts health check and metrics server on port 8000.

Supports JSON logging for production environments via PB_LOG_FORMAT=json.
"""

import logging
import signal
import sys
import time
from src.observability.health_server import HealthServer
from src.observability.json_logger import configure_logging

# Configure logging (reads PB_LOG_LEVEL and PB_LOG_FORMAT from env)
configure_logging(level="INFO", format_type="text")

logger = logging.getLogger(__name__)

# Global server instance for signal handling
server = None


def signal_handler(signum, frame):
    """Graceful shutdown on SIGTERM/SIGINT."""
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    if server:
        server.stop()
    sys.exit(0)


def main():
    """Start health server and run forever."""
    global server

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("Starting Project Builder health server...")

    # Start health server
    server = HealthServer(host='0.0.0.0', port=8000)
    server.start()

    # Mark as ready
    HealthServer.set_ready(True)
    logger.info("Health server ready - container is healthy")

    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        server.stop()


if __name__ == '__main__':
    main()
