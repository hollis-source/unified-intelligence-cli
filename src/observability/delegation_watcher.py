from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol, Dict
import subprocess
import time


class ProcessHandle(Protocol):
    @property
    def pid(self) -> int: ...
    def poll(self) -> Optional[int]: ...  # None if running
    def terminate(self) -> None: ...


class Runner(Protocol):
    def start(self, command: List[str]) -> ProcessHandle: ...


@dataclass
class _SubprocessHandle:
    proc: subprocess.Popen

    @property
    def pid(self) -> int:
        return self.proc.pid

    def poll(self) -> Optional[int]:
        return self.proc.poll()

    def terminate(self) -> None:
        try:
            self.proc.terminate()
        except Exception:
            pass


class SubprocessRunner:
    def start(self, command: List[str]) -> ProcessHandle:
        # Launch background process with stdout/stderr suppressed
        proc = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
        return _SubprocessHandle(proc)


class DelegationWatcher:
    """Supervises two background delegation processes.

    Starts two independent commands, provides health status, and can stop them.
    Uses dependency inversion via Runner for testability.
    """

    def __init__(self, runner: Runner, cmd_a: List[str], cmd_b: List[str]):
        self._runner = runner
        self._cmd_a = cmd_a
        self._cmd_b = cmd_b
        self._p1: Optional[ProcessHandle] = None
        self._p2: Optional[ProcessHandle] = None

    # Helpers
    def _is_running(self, p: Optional[ProcessHandle]) -> bool:
        return bool(p) and p.poll() is None

    def _status_for(self, name: str, p: Optional[ProcessHandle]) -> Dict[str, object]:
        return {"name": name, "pid": getattr(p, "pid", None), "running": self._is_running(p)}

    # API
    def start(self) -> None:
        if self._p1 or self._p2:
            raise RuntimeError("DelegationWatcher already started")
        self._p1 = self._runner.start(self._cmd_a)
        self._p2 = self._runner.start(self._cmd_b)

    def status(self) -> Dict[str, object]:
        s1 = self._status_for("delegate_a", self._p1)
        s2 = self._status_for("delegate_b", self._p2)
        running_count = int(s1["running"]) + int(s2["running"]) if (self._p1 or self._p2) else 0
        if running_count == 2:
            overall = "healthy"
        elif running_count == 1:
            overall = "degraded"
        else:
            overall = "stopped"
        return {"overall": overall, "processes": [s1, s2]}

    def stop(self, grace_seconds: float = 1.0) -> None:
        for p in [self._p1, self._p2]:
            if self._is_running(p):
                try:
                    p.terminate()
                except Exception:
                    pass
        # brief grace period
        deadline = time.time() + max(grace_seconds, 0)
        while time.time() < deadline:
            if not self._is_running(self._p1) and not self._is_running(self._p2):
                break
            time.sleep(0.01)
        self._p1 = None
        self._p2 = None

