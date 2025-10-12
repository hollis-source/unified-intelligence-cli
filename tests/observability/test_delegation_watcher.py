import time
from typing import List, Optional

import pytest

from src.observability.delegation_watcher import DelegationWatcher, ProcessHandle, Runner


class FakeProcess(ProcessHandle):
    def __init__(self, pid: int):
        self._pid = pid
        self._running = True
        self.terminated = False

    @property
    def pid(self) -> int:
        return self._pid

    def poll(self) -> Optional[int]:
        return None if self._running else 0

    def terminate(self) -> None:
        self.terminated = True
        self._running = False

    # helpers for tests
    def crash(self):
        self._running = False


class FakeRunner(Runner):
    def __init__(self):
        self.started: List[List[str]] = []
        self.processes: List[FakeProcess] = []
        self._next_pid = 1000

    def start(self, command: List[str]) -> ProcessHandle:
        self.started.append(command)
        p = FakeProcess(self._next_pid)
        self._next_pid += 1
        self.processes.append(p)
        return p


def test_start_launches_two_processes():
    runner = FakeRunner()
    watcher = DelegationWatcher(runner, ["echo", "A"], ["echo", "B"])

    watcher.start()

    assert len(runner.started) == 2
    assert watcher.status()["overall"] == "healthy"


def test_status_degrades_when_one_process_stops():
    runner = FakeRunner()
    watcher = DelegationWatcher(runner, ["cmd1"], ["cmd2"])
    watcher.start()

    # Simulate crash of first process
    runner.processes[0].crash()

    status = watcher.status()
    assert status["overall"] == "degraded"
    assert status["processes"][0]["running"] is False
    assert status["processes"][1]["running"] is True


def test_stop_terminates_both():
    runner = FakeRunner()
    watcher = DelegationWatcher(runner, ["cmd1"], ["cmd2"])
    watcher.start()

    watcher.stop(grace_seconds=0.01)

    assert all(p.terminated for p in runner.processes)
    assert watcher.status()["overall"] == "stopped"


def test_start_is_idempotent_and_raises_if_already_started():
    runner = FakeRunner()
    watcher = DelegationWatcher(runner, ["cmd1"], ["cmd2"])
    watcher.start()
    with pytest.raises(RuntimeError):
        watcher.start()


def test_status_when_never_started_is_stopped():
    runner = FakeRunner()
    watcher = DelegationWatcher(runner, ["cmd1"], ["cmd2"])
    assert watcher.status()["overall"] == "stopped"

