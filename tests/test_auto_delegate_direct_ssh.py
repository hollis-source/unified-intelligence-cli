import io
import json
import os
import subprocess
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest


def load_hook_module():
    return SourceFileLoader("auto_delegate", ".claude/hooks/auto_delegate.py").load_module()


def test_create_task_file_contains_principles(tmp_path, monkeypatch):
    mod = load_hook_module()
    monkeypatch.chdir(tmp_path)
    tf = mod.create_task_file("Implement feature X")
    p = Path(tf)
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "CLEAN ARCHITECTURE PRINCIPLES TO FOLLOW" in content
    assert "Functions < 20 lines" in content


def test_perform_delegation_summarizes_to_15_lines(monkeypatch, tmp_path):
    mod = load_hook_module()
    monkeypatch.chdir(tmp_path)

    class FakeCompleted:
        def __init__(self, stdout):
            self.stdout = stdout

    long_out = "\n".join([f"Line {i}" for i in range(1, 40)])

    def fake_run(cmd, shell, capture_output, timeout):
        return FakeCompleted(stdout=long_out.encode("utf-8"))

    monkeypatch.setattr(subprocess, "run", fake_run)
    summary = mod.perform_delegation("Research best practices for X and write a guide")
    assert len(summary.splitlines()) <= 15
    assert "Line 1" in summary


def test_print_completion_message_outputs_marker(capsys):
    mod = load_hook_module()
    mod.print_completion_message("Summary line")
    captured = capsys.readouterr().out
    assert "DELEGATION_COMPLETE" in captured
    assert mod.RECURSION_MARKER in captured


def test_main_fallback_on_ssh_failure(monkeypatch, capsys):
    mod = load_hook_module()

    def failing_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="ssh", timeout=1)

    monkeypatch.setattr(subprocess, "run", failing_run)

    # Provide a prompt that will classify as delegate
    prompt = "Refactor the entire authentication system across 5 files"
    monkeypatch.setenv("DELEGATION_DISABLE", "0")
    monkeypatch.setenv("AUGGIE_AVAILABLE", "1")

    monkeypatch.setattr(mod, "read_input", lambda: (prompt, {}))

    # Run main; should fall back to legacy JSON with auggie_prompt
    rc = mod.main()
    assert rc == 0
    out = capsys.readouterr().out.strip()
    js = json.loads(out)
    assert js["action"] == "delegate"
    assert "auggie_prompt" in js
    assert "fallback" in js.get("reason", "").lower()

