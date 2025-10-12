import types
import subprocess
import pytest

from src.utils.auggie_auth import (
    get_execution_mode,
    build_check_command,
    check_auggie_auth,
)


def test_get_execution_mode():
    assert get_execution_mode(None) == "local"
    assert get_execution_mode("") == "local"
    assert get_execution_mode("local") == "local"
    assert get_execution_mode("localhost") == "local"
    assert get_execution_mode("this") == "local"
    assert get_execution_mode("root@1.2.3.4") == "remote"


def test_build_check_command():
    cmd = build_check_command()
    assert "auggie" in cmd
    assert "session list" in cmd or "--help" in cmd


def _make_completed(stdout: str = "", stderr: str = "", returncode: int = 0):
    cp = types.SimpleNamespace()
    cp.stdout = stdout
    cp.stderr = stderr
    cp.returncode = returncode
    return cp


def test_check_local_success(monkeypatch):
    def fake_run(cmd, shell, capture_output, text, timeout):
        assert shell is True
        assert "auggie" in cmd
        return _make_completed(stdout="OK", stderr="", returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = check_auggie_auth()
    assert res.success is True
    assert res.mode == "local"
    assert "OK" in res.stdout


def test_check_local_failure(monkeypatch):
    def fake_run(cmd, shell, capture_output, text, timeout):
        raise subprocess.CalledProcessError(1, cmd, output="", stderr="not authenticated")

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = check_auggie_auth()
    assert res.success is False
    assert "failed" in res.message.lower()
    assert "not authenticated" in (res.stderr or "")


def test_check_remote_success(monkeypatch):
    def fake_run(cmd, shell, capture_output, text, timeout):
        assert cmd.startswith("ssh root@1.2.3.4 ")
        assert "auggie" in cmd
        return _make_completed(stdout="SSH OK", stderr="", returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = check_auggie_auth(remote_host="root@1.2.3.4")
    assert res.success is True
    assert res.mode == "remote"
    assert "SSH OK" in res.stdout


def test_check_remote_with_jump(monkeypatch):
    def fake_run(cmd, shell, capture_output, text, timeout):
        assert cmd.startswith("ssh -J syd2 root@2.2.2.2 ")
        return _make_completed(stdout="JUMP OK", stderr="", returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = check_auggie_auth(remote_host="root@2.2.2.2", jump_host="syd2")
    assert res.success is True
    assert "JUMP OK" in res.stdout


def test_check_remote_failure(monkeypatch):
    def fake_run(cmd, shell, capture_output, text, timeout):
        raise subprocess.CalledProcessError(255, cmd, output="", stderr="permission denied")

    monkeypatch.setattr(subprocess, "run", fake_run)
    res = check_auggie_auth(remote_host="root@5.6.7.8")
    assert res.success is False
    assert "permission denied" in (res.stderr or "")

