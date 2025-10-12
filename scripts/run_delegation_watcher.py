#!/usr/bin/env python3
"""
Run DelegationWatcher as a background daemon in production.

Reads two commands from environment variables and supervises them:
- DELEGATE_CMD_A (default: echo 'delegate A')
- DELEGATE_CMD_B (default: echo 'delegate B')

Usage (production):
  nohup venv/bin/python scripts/run_delegation_watcher.py >> logs/delegation_watcher.log 2>&1 &

Clean Code: small functions, explicit error handling, dependency inversion via Runner.
"""
import os
import shlex
import signal
import sys
import time
from typing import List

from src.observability.delegation_watcher import DelegationWatcher, SubprocessRunner


def _parse_command(cmd: str) -> List[str]:
    if not cmd:
        return ["bash", "-lc", "echo 'noop'"]
    # Use shlex.split for proper quoting
    return shlex.split(cmd)


def main() -> int:
    try:
        cmd_a = os.getenv("DELEGATE_CMD_A", "bash -lc 'echo delegate A'")
        cmd_b = os.getenv("DELEGATE_CMD_B", "bash -lc 'echo delegate B'")

        watcher = DelegationWatcher(
            runner=SubprocessRunner(),
            cmd_a=_parse_command(cmd_a),
            cmd_b=_parse_command(cmd_b),
        )
        watcher.start()

        # Write simple PID file if LOGS dir exists
        pid_dir = os.path.join("logs")
        try:
            os.makedirs(pid_dir, exist_ok=True)
            with open(os.path.join(pid_dir, "delegation_watcher.pid"), "w", encoding="utf-8") as f:
                f.write(str(os.getpid()))
        except Exception:
            pass  # Non-fatal

        # Graceful shutdown handlers
        stopping = False

        def _stop(signum, frame):
            nonlocal stopping
            if not stopping:
                stopping = True
                try:
                    watcher.stop()
                finally:
                    sys.exit(0)

        signal.signal(signal.SIGINT, _stop)
        signal.signal(signal.SIGTERM, _stop)

        # Keep process alive; could be extended to expose health/status
        while not stopping:
            time.sleep(1.0)
    except Exception as e:
        # Print to stderr to surface in logs
        print(f"DelegationWatcher failed to start: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

