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


def test_balanced_mode_suggest_for_moderate_complexity():
    # keyword_score: write tests (3) + >50 lines (2) => 5 => suggest in balanced mode
    out = run_hook_with_input(
        "Please write tests for the module; expect around >50 lines",
        extra_env={"DELEGATION_MODE": "balanced"},
    )
    assert out["action"] == "suggest"


def test_balanced_mode_pass_for_simple_prompt():
    out = run_hook_with_input(
        "Fix typo in line 1",
        extra_env={"DELEGATION_MODE": "balanced"},
    )
    assert out["action"] == "pass"

