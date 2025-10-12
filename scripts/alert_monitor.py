#!/usr/bin/env python3
"""Alert Monitor Daemon for PriorityWorker

Standalone daemon that monitors PriorityWorker health and sends alerts.
Can be run as cron job or continuous daemon.

Usage:
    python3 scripts/alert_monitor.py --config config/alerting.yaml --daemon
    python3 scripts/alert_monitor.py --config config/alerting.yaml --once

Generated from ULTRATHINK design on 2025-10-04.
"""

import argparse
import sys
import yaml
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.priority_queue.adapters.alert_manager import AlertManager


def load_config(config_path: Path) -> dict:
    """Load alerting configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description='PriorityWorker Alert Monitor')
    parser.add_argument(
        '--config',
        type=Path,
        default=Path('config/alerting.yaml'),
        help='Path to alerting configuration file'
    )
    parser.add_argument(
        '--daemon',
        action='store_true',
        help='Run in continuous daemon mode'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run single check and exit (for cron)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        help='Override check interval seconds (daemon mode only)'
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"Failed to load config: {e}")
        sys.exit(1)

    # Initialize AlertManager
    alert_manager = AlertManager(config)

    if args.once:
        # Single check mode (for cron)
        print("Running single health check...")
        alert_manager.check_and_alert()
        print("Check complete")
        sys.exit(0)

    elif args.daemon:
        # Continuous daemon mode
        interval = args.interval or config.get('check_interval_seconds', 60)
        print(f"Starting alert monitor daemon (interval: {interval}s)")
        try:
            alert_manager.monitor_loop(interval_seconds=interval)
        except KeyboardInterrupt:
            print("\nAlert monitor stopped")
            sys.exit(0)

    else:
        print("Error: Must specify --daemon or --once")
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
