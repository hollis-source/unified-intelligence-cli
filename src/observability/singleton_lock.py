"""Singleton process lock using a PID file.

Clean Architecture: small utility adapter for process coordination.
SOLID: SRP (locking only), DIP (no side effects beyond filesystem and OS)
"""
from __future__ import annotations

import os
import atexit
from pathlib import Path
from typing import Optional

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None  # Fallback to os.kill check


class SingletonLock:
    """Simple PID file based singleton lock.

    Usage:
      lock = SingletonLock(pid_file)
      if not lock.acquire():
          # already running
          return False
      # do work
      # released automatically at exit
    """

    def __init__(self, pid_file: str | Path) -> None:
        self.pid_path = Path(pid_file)
        self._owned = False
        atexit.register(self.release)

    def _process_exists(self, pid: int) -> bool:
        if pid <= 0:
            return False
        if psutil is not None:
            try:
                psutil.Process(pid)
                return True
            except Exception:
                return False
        # Fallback: POSIX check
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def acquire(self) -> bool:
        """Try to acquire the singleton lock. Returns True if acquired."""
        try:
            if self.pid_path.exists():
                try:
                    existing = int(self.pid_path.read_text().strip())
                except Exception:
                    existing = -1
                if self._process_exists(existing):
                    return False
                # Stale PID: remove
                try:
                    self.pid_path.unlink(missing_ok=True)
                except Exception:
                    return False
            # Write our PID
            self.pid_path.parent.mkdir(parents=True, exist_ok=True)
            self.pid_path.write_text(str(os.getpid()))
            self._owned = True
            return True
        except Exception:
            return False

    def release(self) -> None:
        """Release the lock if owned by this process."""
        if not self._owned:
            return
        try:
            if self.pid_path.exists():
                current = self.pid_path.read_text().strip()
                if current == str(os.getpid()):
                    self.pid_path.unlink(missing_ok=True)
        finally:
            self._owned = False

