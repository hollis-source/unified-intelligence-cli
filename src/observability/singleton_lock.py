from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


class SingletonLock:
    def __init__(self, pid_file: Path) -> None:
        self.pid_file = Path(pid_file)
        self._acquired: bool = False

    def _is_process_running(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        else:
            return True

    def acquire(self) -> bool:
        if self.pid_file.exists():
            try:
                content = self.pid_file.read_text().strip()
                pid = int(content)
            except Exception:
                pid = -1
            if pid > 0 and self._is_process_running(pid):
                return False
            # stale pid file; clean it
            try:
                self.pid_file.unlink(missing_ok=True)
            except Exception:
                pass
        # write our pid
        try:
            self.pid_file.parent.mkdir(parents=True, exist_ok=True)
            self.pid_file.write_text(str(os.getpid()))
            self._acquired = True
            return True
        except Exception:
            return False

    def release(self) -> None:
        if self._acquired:
            try:
                self.pid_file.unlink(missing_ok=True)
            finally:
                self._acquired = False

