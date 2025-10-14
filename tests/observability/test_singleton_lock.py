import os
import tempfile
from pathlib import Path

from src.observability.singleton_lock import SingletonLock


def test_acquire_and_release_allows_single_instance(tmp_path: Path):
    pid_file = tmp_path / "worker.pid"

    lock1 = SingletonLock(pid_file)
    assert lock1.acquire() is True  # First acquire succeeds

    lock2 = SingletonLock(pid_file)
    assert lock2.acquire() is False  # Second acquire sees running process

    # Release and allow reacquire
    lock1.release()
    assert lock2.acquire() is True


def test_stale_pid_is_cleaned_and_acquired(tmp_path: Path):
    pid_file = tmp_path / "worker.pid"

    # Write a stale PID (unlikely to exist)
    pid_file.write_text("999999")

    lock = SingletonLock(pid_file)
    assert lock.acquire() is True  # Should clean stale file and acquire

    # Clean up
    lock.release()

