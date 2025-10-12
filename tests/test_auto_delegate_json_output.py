import json
import os
import subprocess


def run_hook_with_input(text: str, extra_env=None) -> dict:
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    p = subprocess.run(
        ["python3", ".claude/hooks/auto_delegate.py"],
        input=text.encode("utf-8"),
        capture_output=True,
        env=env,
        check=True,
    )
    out = p.stdout.decode("utf-8", errors="ignore").strip()
    return json.loads(out)


def test_delegation_emits_json_by_default():
    out = run_hook_with_input("Research best practices and write docs")
    assert out["action"] == "delegate"
    assert "auggie_prompt" in out and "Auto-delegated task" in out["auggie_prompt"]


def test_delegation_ssh_mode_falls_back_to_json_on_error():
    # Force SSH mode; without proper SSH, the hook should fall back to JSON
    out = run_hook_with_input(
        "Generate comprehensive test suite for the API",
        extra_env={"DELEGATION_EXECUTION": "ssh"},
    )
    assert out["action"] == "delegate"
    assert "auggie_prompt" in out
