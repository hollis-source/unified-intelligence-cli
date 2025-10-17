from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional, Protocol


class ProcessHandle(Protocol):
    @property
    def pid(self) -> int: ...

    def poll(self) -> Optional[int]: ...

    def terminate(self) -> None: ...


class Runner(Protocol):
    def start(self, command: List[str]) -> ProcessHandle: ...


@dataclass
class _ProcInfo:
    command: List[str]
    handle: Optional[ProcessHandle] = None


class DelegationWatcher:
    def __init__(self, runner: Runner, *commands: List[str]) -> None:
        if len(commands) != 2:
            raise ValueError("DelegationWatcher expects exactly two commands")
        self._runner = runner
        self._procs: List[_ProcInfo] = [_ProcInfo(list(commands[0])), _ProcInfo(list(commands[1]))]
        self._started = False

    def start(self) -> None:
        if self._started:
            raise RuntimeError("already_started")
        for p in self._procs:
            p.handle = self._runner.start(p.command)
        self._started = True

    def stop(self, grace_seconds: float = 1.0) -> None:
        for p in self._procs:
            if p.handle is not None:
                try:
                    p.handle.terminate()
                except Exception:
                    pass
        time.sleep(grace_seconds)
        self._started = False

    def status(self) -> dict:
        if not self._started:
            return {"overall": "stopped", "processes": []}
        infos = []
        running_flags = []
        for p in self._procs:
            running = (p.handle is not None and p.handle.poll() is None)
            running_flags.append(running)
            infos.append({"pid": getattr(p.handle, "pid", None) if p.handle else None, "running": running, "command": p.command})
        overall = "healthy" if all(running_flags) else ("degraded" if any(running_flags) else "down")
        return {"overall": overall, "processes": infos}

