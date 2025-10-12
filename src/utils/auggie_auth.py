from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import shlex
import subprocess


@dataclass(frozen=True)
class AuthCheckResult:
    success: bool
    mode: str
    stdout: str | None
    stderr: str | None
    message: str


def get_execution_mode(remote_host: Optional[str]) -> str:
    v = (remote_host or "").strip().lower()
    return "local" if v in ("", "local", "localhost", "this") else "remote"


def build_check_command() -> str:
    # Prefer a command that exercises auth without side effects
    return "auggie session list --limit 1"


def _escape_single_quotes(s: str) -> str:
    return s.replace("'", "'\\''")


def _run(cmd: str, timeout: int = 10) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)


def _run_remote(host: str, cmd: str, jump_host: Optional[str], timeout: int = 10) -> subprocess.CompletedProcess:
    safe = _escape_single_quotes(cmd)
    prefix = f"ssh -J {shlex.quote(jump_host)} {shlex.quote(host)} " if jump_host else f"ssh {shlex.quote(host)} "
    return _run(f"{prefix}'{safe}'", timeout=timeout)


def check_auggie_auth(remote_host: Optional[str] = None, jump_host: Optional[str] = None, timeout: int = 10) -> AuthCheckResult:
    mode = get_execution_mode(remote_host)
    cmd = build_check_command()
    try:
      if mode == "local":
          res = _run(cmd, timeout=timeout)
      else:
          assert remote_host, "remote_host must be provided for remote mode"
          res = _run_remote(remote_host, cmd, jump_host, timeout=timeout)
      ok = res.returncode == 0
      msg = "authentication verified" if ok else "authentication check failed"
      return AuthCheckResult(ok, mode, res.stdout, res.stderr, msg)
    except subprocess.CalledProcessError as e:
      return AuthCheckResult(False, mode, getattr(e, 'output', ''), getattr(e, 'stderr', ''), 'authentication check failed')
    except Exception as e:
      return AuthCheckResult(False, mode, None, str(e), 'authentication check failed')

