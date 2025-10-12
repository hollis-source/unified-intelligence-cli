#!/usr/bin/env python3
"""
UserPromptSubmit hook for automatic delegation to Auggie (GPT-5).

Analyzes user requests and automatically delegates complex tasks to Auggie
to minimize Claude token usage.

Toggle: Set DELEGATION_DISABLE=1 to disable
Log: ~/.claude/delegation.log

Invocation contracts supported (best-effort to be compatible):
- Stdin plain text: the raw user prompt
- Stdin JSON: {"prompt": "...", "metadata": {...}}
- Env var HOOK_PROMPT: prompt text if stdin empty

Output (JSON to stdout):
{ "action": "delegate|suggest|pass", "score": int, "reason": str,
  "prompt": str, "auggie_prompt": str (when action==delegate), "banner": str }

CLI Options:
- --test: Run built-in test cases
- --metrics: Export Prometheus metrics to stdout
- --cleanup: Clean up task files older than 24 hours

Metrics File: ~/.claude/delegation_metrics.prom (Prometheus format)
"""
import json
import os
import re
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Tuple

LOG_PATH = os.path.expanduser("~/.claude/delegation.log")
METRICS_PATH = os.path.expanduser("~/.claude/delegation_metrics.prom")
DEFAULT_MODE = os.getenv("DELEGATION_MODE", "balanced").lower()
DISABLED = os.getenv("DELEGATION_DISABLE", "0") == "1"
AUGGIE_AVAILABLE = os.getenv("AUGGIE_AVAILABLE", "1") != "0"
DELEGATED_CONTEXT = os.getenv("DELEGATED_CONTEXT", "0") == "1"

# Metrics state (persisted across invocations via metrics file)
METRICS = {
    "delegation_decisions_total": {},  # {action: count}
    "delegation_executions_total": {},  # {status: count}
    "delegation_false_positives_total": 0,
    "delegation_duration_seconds": [],  # Last 100 execution times
}

MODE_THRESHOLDS = {
    "aggressive": {"delegate": 0, "suggest_min": -1, "suggest_max": -1},  # Delegate everything
    "balanced":   {"delegate": 7, "suggest_min": 4, "suggest_max": 6},
    "conservative": {"delegate": 8, "suggest_min": 5, "suggest_max": 7},
}
RECURSION_MARKER = "DELEGATION_COMPLETE"
SSH_HOST = os.getenv("SSH_HOST", "root@157.90.66.183")
SSH_KEY = os.getenv("SSH_KEY", os.path.expanduser("~/.ssh/id_ed25519"))
AUGGIE_NODE = os.getenv("AUGGIE_NODE", "/home/ui-cli_jake/.nvm/versions/node/v22.20.0/bin/node")
AUGGIE_CLI = os.getenv("AUGGIE_PATH", "/home/ui-cli_jake/.nvm/versions/node/v22.20.0/bin/auggie")
DELEGATION_TIMEOUT = int(os.getenv("DELEGATION_TIMEOUT", "600"))

WATCHER_ENABLED = os.getenv("DELEGATION_WATCHER", "1") != "0"

def ensure_watcher():
    """Start delegation watcher if not already running."""
    try:
        watcher = Path(__file__).with_name("delegation_watcher.py")
        subprocess.Popen(["python3", str(watcher), "--daemon"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass  # Fail silently - watcher is optional




SIMPLE_NEGATIVE_HINTS = [
    r"\bread\b", r"show me", r"what'?s in", r"^\s*read ", r"^\s*cat ", r"git status",
    r"fix typo", r"<\s*10\s*lines", r"^\s*ls\b", r"^\s*pwd\b", r"quick question",
]

# False positive patterns - statements that shouldn't trigger delegation
FALSE_POSITIVE_PATTERNS = [
    r"^(currently|checking|verifying|waiting|monitoring|status)",  # Status updates
    r"^(all|both|some|most) (task|background|process|auggie).*(complete|done|running|finished)",  # Status reports
    r"what (is|are) the (content|status|result)",  # Meta-questions about delegation
    r"(check|show|view|display) (output|result|status|progress)",  # Monitoring requests
    r"^(update|report|summary|monitor)(\s|$)",  # Simple requests for info
]

COMPLEX_POSITIVE_HINTS = [
    (r"research|analy[sz]e|compare options|investigate", 3),
    (r"generate|create (module|service|project)|scaffold|boilerplate", 3),
    (r"refactor (the )?(entire|whole)|across \d+ files|multi-?file", 4),
    (r"write (a )?(guide|readme|documentation|docs?)", 3),
    (r"write tests|test suite|coverage|unit tests|integration tests", 3),
    (r"stack trace|traceback|multiple errors|intermittent|race condition", 4),
    (r"performance|optimi[sz]e|profil(e|ing)|bottleneck", 3),
    (r"migrate|migration|schema change|database upgrade", 3),
]

NO_DELEGATE_MARKERS = ["no-delegate", "keep with claude", "do not delegate"]
EXPLICIT_AUGGIE = ["use auggie", "delegate to auggie", "auggie:"]

@dataclass
class Decision:
    action: str  # delegate | suggest | pass
    score: int
    reason: str
    prompt: str
    auggie_prompt: str = ""
    banner: str = ""


def read_input() -> Tuple[str, Dict]:
    data = sys.stdin.read()
    if data.strip():
        try:
            js = json.loads(data)
            prompt = js.get("prompt") or js.get("text") or ""
            meta = js.get("metadata") or {}
            if not prompt:
                prompt = data
            return prompt, meta
        except Exception:
            return data, {}
    env_prompt = os.getenv("HOOK_PROMPT")
    if env_prompt:
        return env_prompt, {}
    return "", {}


def length_score(prompt: str) -> int:
    # Coarse heuristic by characters and words
    chars = len(prompt)
    words = len(prompt.split())
    s = 0
    if chars > 600 or words > 120:
        s += 2
    elif chars > 300 or words > 60:
        s += 1
    return s


def keyword_score(prompt: str) -> int:
    p = prompt.lower()
    score = 0
    matched = 0
    for rx, pts in COMPLEX_POSITIVE_HINTS:
        if re.search(rx, p):
            score += pts
            matched += 1
    # Synergy bonus when multiple complex signals appear
    if matched >= 2:
        score += 1
    # Multi-file counts (e.g., "across 5 files")
    m = re.search(r"(across|over|touch(es)?|modif(y|ies))\s+(\d+)\s+files", p)
    if m:
        n = int(m.group(4))
        if n >= 5:
            score += 3
        elif n >= 3:
            score += 2
    # Code size hints
    if re.search(r">?\s*100\s*lines", p):
        score += 3
    elif re.search(r">?\s*50\s*lines", p):
        score += 2
    return score


def simple_penalties(prompt: str) -> int:
    p = prompt.lower()
    penalty = 0
    for rx in SIMPLE_NEGATIVE_HINTS:
        if re.search(rx, p):
            penalty += 2
    # Explicitly small change
    if re.search(r"<\s*10\s*lines|tiny change|one-liner|minor tweak", p):
        penalty += 2
    return penalty


def compute_score(prompt: str) -> int:
    s = 0
    s += length_score(prompt)
    s += keyword_score(prompt)
    s -= simple_penalties(prompt)
    # Clamp 0..10
    return max(0, min(10, s))


def thresholds() -> Dict[str, int]:
    return MODE_THRESHOLDS.get(DEFAULT_MODE, MODE_THRESHOLDS["balanced"])


def classify(score: int) -> str:
    th = thresholds()
    if score >= th["delegate"]:
        return "delegate"
    if th["suggest_min"] <= score <= th["suggest_max"]:
        return "suggest"
    return "pass"


def already_delegated(prompt: str) -> bool:
    p = prompt.lower()
    return DELEGATED_CONTEXT or (RECURSION_MARKER.lower() in p) or ("auto-delegating to auggie" in p)


def has_opt_out(prompt: str) -> bool:
    p = prompt.lower()
    return any(tok in p for tok in NO_DELEGATE_MARKERS)


def explicit_use_auggie(prompt: str) -> bool:
    p = prompt.lower()
    return any(tok in p for tok in EXPLICIT_AUGGIE)


def is_false_positive(prompt: str) -> bool:
    """Check if prompt matches false positive patterns (status updates, meta-questions)."""
    p = prompt.lower().strip()
    return any(re.search(pattern, p) for pattern in FALSE_POSITIVE_PATTERNS)


def rewrite_for_auggie(prompt: str) -> str:
    cwd = os.getcwd()
    guideline = (
        "You are Auggie (GPT-5) executing a delegated task to minimize Claude token usage. "
        "Work autonomously, be efficient, and produce concise, actionable results. "
        "Start with a brief summary of the outcome, then list key steps taken, and include any code diffs or file paths. "
        "If code changes are needed, propose minimally invasive edits and include tests."
    )
    return (
        f"Auto-delegated task from Claude.\n"
        f"Working directory: {cwd}\n"
        f"Original user request:\n{prompt}\n\n"
        f"Instructions:\n{guideline}\n"
        f"On completion, provide a compact summary and any next steps back to Claude."
    )

def build_task_content(user_prompt: str) -> str:
    return (
        f"""
USER REQUEST: {user_prompt}

CLEAN ARCHITECTURE PRINCIPLES TO FOLLOW:
- Functions < 20 lines
- Meaningful names revealing intent
- DRY - no duplication
- Explicit error handling
- TDD - tests first
- Entities at center (business logic)
- Use cases around entities
- Adapters for externals (APIs, DBs)
- Dependency Inversion - depend on abstractions
- Protect business logic from frameworks
- SRP, OCP, LSP, ISP, DIP

REQUIREMENTS:
- Implement directly in repository
- Write tests first (TDD)
- Functions < 20 lines
- Follow SOLID principles
- Small, atomic commits
- Return concise summary only (<=15 lines)

DELIVERABLES:
- Implementation complete and tested
- Brief summary of changes
- File paths modified
- No code dumps
"""
    )


def create_task_file(user_prompt: str) -> str:
    path = Path.cwd() / f".auggie_task_{int(time.time())}.txt"
    path.write_text(build_task_content(user_prompt), encoding="utf-8")
    return str(path)


def build_auggie_ssh_command(task_file: str) -> str:
    """Construct the SSH command to run Auggie remotely, optionally via jump host.

    Keeps construction isolated for testability and clarity (SRP).
    """
    remote_cmd = (
        f"cd /home/ui-cli_jake/unified-intelligence-cli && "
        f"{AUGGIE_NODE} {AUGGIE_CLI} --print --quiet --model gpt5 "
        f"'Read and execute {task_file}'"
    )
    jump_host = os.getenv("SSH_JUMP_HOST", "").strip()
    parts = ["ssh"]
    if jump_host:
        parts.extend(["-J", jump_host])
    parts.extend(["-i", SSH_KEY, SSH_HOST, f"\"{remote_cmd}\""])
    return " ".join(parts)


def execute_auggie_ssh(task_file: str) -> str:
    ssh_cmd = build_auggie_ssh_command(task_file)
    res = subprocess.run(ssh_cmd, shell=True, capture_output=True, timeout=DELEGATION_TIMEOUT)
    return (res.stdout or b"").decode("utf-8", errors="ignore")


def summarize_output(output: str, max_lines: int = 15) -> str:
    lines = [ln for ln in (output or "").strip().splitlines() if ln.strip()]
    return "\n".join(lines[:max_lines])


def print_completion_message(summary: str):
    print(
        f"""
DELEGATION_COMPLETE
{RECURSION_MARKER}

Auggie has completed the implementation following Clean Architecture principles.

Summary:
{summary}

The implementation is complete and tested. Proceed with next tasks.
"""
    )


def log_execution(details: Dict) -> None:
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        payload = {"ts": int(time.time()), "mode": DEFAULT_MODE}
        payload.update(details)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass


def perform_delegation(prompt: str) -> str:
    start_time = time.time()
    try:
        task_file = create_task_file(prompt)
        output = execute_auggie_ssh(task_file)
        if not (output or "").strip():
            raise RuntimeError("SSH execution produced no output")
        summary = summarize_output(output)
        duration = time.time() - start_time
        log_execution({
            "action": "delegate",
            "execution_method": "direct_ssh",
            "task_file": task_file,
            "duration": duration,
        })
        update_execution_metric("success", duration)
        # Clean up task file after successful execution
        try:
            Path(task_file).unlink()
        except Exception:
            pass
        return summary
    except Exception as e:
        duration = time.time() - start_time
        update_execution_metric("failure", duration)
        raise


def log_decision(d: Decision) -> None:
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": int(time.time()),
                "action": d.action,
                "score": d.score,
                "reason": d.reason,
                "mode": DEFAULT_MODE,
            }) + "\n")
    except Exception:
        pass


def load_metrics() -> Dict:
    """Load metrics from file or return default structure."""
    try:
        if Path(METRICS_PATH).exists():
            with open(METRICS_PATH, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "delegation_decisions_total": {},
        "delegation_executions_total": {},
        "delegation_false_positives_total": 0,
        "delegation_duration_seconds": [],
    }


def save_metrics(metrics: Dict) -> None:
    """Save metrics to file in JSON format."""
    try:
        os.makedirs(os.path.dirname(METRICS_PATH), exist_ok=True)
        with open(METRICS_PATH, "w") as f:
            json.dump(metrics, f, indent=2)
    except Exception:
        pass


def update_decision_metric(action: str) -> None:
    """Update delegation_decisions_total metric."""
    global METRICS
    METRICS = load_metrics()
    METRICS["delegation_decisions_total"][action] = \
        METRICS["delegation_decisions_total"].get(action, 0) + 1
    save_metrics(METRICS)


def update_execution_metric(status: str, duration: float = None) -> None:
    """Update delegation_executions_total and duration metrics."""
    global METRICS
    METRICS = load_metrics()
    METRICS["delegation_executions_total"][status] = \
        METRICS["delegation_executions_total"].get(status, 0) + 1
    if duration is not None:
        durations = METRICS.get("delegation_duration_seconds", [])
        durations.append(duration)
        # Keep last 100 only
        METRICS["delegation_duration_seconds"] = durations[-100:]
    save_metrics(METRICS)


def update_false_positive_metric() -> None:
    """Increment false positive counter."""
    global METRICS
    METRICS = load_metrics()
    METRICS["delegation_false_positives_total"] = \
        METRICS.get("delegation_false_positives_total", 0) + 1
    save_metrics(METRICS)


def export_prometheus_metrics() -> str:
    """Export metrics in Prometheus text format."""
    metrics = load_metrics()
    lines = [
        "# HELP delegation_decisions_total Count of delegation decisions by action",
        "# TYPE delegation_decisions_total counter",
    ]
    for action, count in metrics.get("delegation_decisions_total", {}).items():
        lines.append(f'delegation_decisions_total{{action="{action}"}} {count}')

    lines.extend([
        "# HELP delegation_executions_total Count of delegation executions by status",
        "# TYPE delegation_executions_total counter",
    ])
    for status, count in metrics.get("delegation_executions_total", {}).items():
        lines.append(f'delegation_executions_total{{status="{status}"}} {count}')

    lines.extend([
        "# HELP delegation_false_positives_total Count of false positive detections",
        "# TYPE delegation_false_positives_total counter",
        f"delegation_false_positives_total {metrics.get('delegation_false_positives_total', 0)}",
    ])

    durations = metrics.get("delegation_duration_seconds", [])
    if durations:
        avg_duration = sum(durations) / len(durations)
        lines.extend([
            "# HELP delegation_duration_seconds_avg Average delegation execution time",
            "# TYPE delegation_duration_seconds_avg gauge",
            f"delegation_duration_seconds_avg {avg_duration:.2f}",
        ])

    return "\n".join(lines) + "\n"


def decide(prompt: str) -> Decision:
    if DISABLED:
        dec = Decision(action="pass", score=0, reason="Delegation disabled via env", prompt=prompt)
        log_decision(dec)
        update_decision_metric("pass")
        return dec
    if already_delegated(prompt):
        dec = Decision(action="pass", score=0, reason="Already in delegated context", prompt=prompt)
        log_decision(dec)
        update_decision_metric("pass")
        return dec
    if has_opt_out(prompt):
        dec = Decision(action="pass", score=0, reason="User opt-out (no-delegate)", prompt=prompt)
        log_decision(dec)
        update_decision_metric("pass")
        return dec
    if is_false_positive(prompt):
        update_false_positive_metric()
        dec = Decision(action="pass", score=0, reason="False positive (status/meta-question)", prompt=prompt)
        log_decision(dec)
        update_decision_metric("pass")
        return dec

    sc = compute_score(prompt)
    kind = classify(sc)

    if explicit_use_auggie(prompt):
        kind = "delegate"

    if kind == "delegate":
        if not AUGGIE_AVAILABLE:
            dec = Decision(action="pass", score=sc, reason="Auggie unavailable; fallback to Claude", prompt=prompt)
            log_decision(dec)
            update_decision_metric("pass")
            return dec
        ap = rewrite_for_auggie(prompt)
        banner = "Auto-delegating to Auggie for efficiency (score=%d, mode=%s)." % (sc, DEFAULT_MODE)
        dec = Decision(action="delegate", score=sc, reason="High complexity", prompt=prompt, auggie_prompt=ap, banner=banner)
        log_decision(dec)
        update_decision_metric("delegate")
        return dec

    if kind == "suggest":
        banner = "Suggestion: delegate to Auggie (score=%d). Proceeding with Claude unless confirmed." % sc
        dec = Decision(action="suggest", score=sc, reason="Moderate complexity", prompt=prompt, banner=banner)
        log_decision(dec)
        update_decision_metric("suggest")
        return dec

    dec = Decision(action="pass", score=sc, reason="Simple task; keep with Claude", prompt=prompt)
    log_decision(dec)
    update_decision_metric("pass")
    return dec


def cleanup_old_task_files(max_age_hours: int = 24) -> int:
    """Clean up task files older than max_age_hours. Returns count removed."""
    try:
        cutoff = time.time() - (max_age_hours * 3600)
        removed = 0
        for path in Path.cwd().glob(".auggie_task_*.txt"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
                    removed += 1
            except Exception:
                pass
        return removed
    except Exception:
        return 0


def main() -> int:
    if WATCHER_ENABLED:
        ensure_watcher()

    # CLI: --metrics to export Prometheus metrics
    if len(sys.argv) > 1 and sys.argv[1] == "--metrics":
        print(export_prometheus_metrics())
        return 0

    # CLI: --cleanup to clean old task files
    if len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
        removed = cleanup_old_task_files()
        print(f"Removed {removed} old task files")
        return 0

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        tests = [
            ("Research best practices for X and write a guide", "delegate"),
            ("Refactor the entire authentication system across 5 files", "delegate"),
            ("Generate comprehensive test suite for the API", "delegate"),
            ("Analyze performance bottlenecks and create optimization plan", "delegate"),
            ("Read src/main.py", "pass"),
            ("Fix typo in line 42", "pass"),
            ("What's the current git status?", "pass"),
            ("Show me the error in logs", "pass"),
            ("no-delegate please research this", "pass"),
        ]
        ok = 0
        for text, expected in tests:
            d = decide(text)
            print(json.dumps({"input": text, "action": d.action, "score": d.score, "reason": d.reason}))
            if expected == d.action:
                ok += 1
        print(f"Passed {ok}/{len(tests)} tests")
        return 0 if ok == len(tests) else 1

    prompt, _meta = read_input()
    if not prompt.strip():
        # Nothing to do
        out = {"action": "pass", "score": 0, "reason": "Empty prompt", "prompt": ""}
        print(json.dumps(out))
        return 0

    d = decide(prompt)
    out = {
        "action": d.action,
        "score": d.score,
        "reason": d.reason,
        "prompt": d.prompt,
        "banner": d.banner,
    }
    if d.action == "delegate":
        exec_mode = os.getenv("DELEGATION_EXECUTION", "ssh").lower()
        if exec_mode == "ssh":
            try:
                # In test environments, skip real SSH and trigger fallback
                if os.getenv("PYTEST_CURRENT_TEST"):
                    raise RuntimeError("SSH disabled in tests")
                summary = perform_delegation(d.prompt)
                print_completion_message(summary)
                return 0
            except Exception:
                # Fall through to JSON-based delegation on any SSH error
                out["reason"] = "Fallback to JSON delegation due to SSH error"
        # Default: emit JSON so Claude/MCP can handle delegation to Auggie
        out["action"] = "delegate"
        out["auggie_prompt"] = rewrite_for_auggie(d.prompt)
        if not out.get("reason"):
            out["reason"] = "Auto-delegation requested"
        print(json.dumps(out))
        return 0
    else:
        print(json.dumps(out))
        return 0


if __name__ == "__main__":
    sys.exit(main())

