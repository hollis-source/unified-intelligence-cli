"""Main entry point for endpoint monitoring daemon.

Usage:
    python -m src.monitoring [--config path/to/config.yaml] [--metrics-port 9090]
"""

import argparse
import asyncio
import logging
import sys

from .config import ConfigLoader
from .daemon import EndpointMonitoringDaemon


def setup_logging(level: str = "INFO"):
    """Configure logging for daemon.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Endpoint monitoring and auto-wake daemon"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config/endpoints.yaml",
        help="Path to configuration file (default: config/endpoints.yaml)",
    )

    parser.add_argument(
        "--metrics-port",
        type=int,
        default=9090,
        help="Port for Prometheus metrics endpoint (default: 9090)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO)",
    )

    return parser.parse_args()


async def main():
    """Main entry point."""
    args = parse_args()

    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    try:
        # Load configuration
        logger.info(f"Loading configuration from {args.config}")
        config = ConfigLoader.load_from_file(args.config)
        logger.info(
            f"Configuration loaded: {len(config.endpoints)} endpoints, "
            f"{len(config.fallback_chains)} fallback chains"
        )

        # Create and start daemon
        daemon = EndpointMonitoringDaemon(
            config=config, metrics_port=args.metrics_port
        )
        await daemon.start()

    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Ctrl+C is handled by signal handlers
        pass
