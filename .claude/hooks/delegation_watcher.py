#!/usr/bin/env python3
"""
Context-aware delegation watcher.
Monitors todos.json for complex discovered work and delegates automatically.
"""
import json
import os
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from auto_delegate import compute_score, perform_delegation, rewrite_for_auggie

TODO_PATH = Path.cwd() / ".claude" / "todos.json"
PID_FILE = Path.cwd() / ".claude" / "delegation_watcher.pid"
POLL_SECONDS = 2


def _write_pidfile() -> bool:
    """Write PID file for singleton enforcement."""
    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text().strip())
            # Check if process still running
            os.kill(old_pid, 0)
            print(f"Watcher already running with PID {old_pid}", file=sys.stderr)
            return False
        except (OSError, ValueError):
            # Process not running, remove stale PID file
            PID_FILE.unlink()

    PID_FILE.write_text(str(os.getpid()))
    return True


def process_todos_once(todo_path: Path, seen: set) -> int:
    """Process todos once, return count of delegations triggered."""
    if not todo_path.exists():
        return 0

    try:
        items = json.loads(todo_path.read_text())
        delegated = 0

        for item in items:
            # Create unique key from todo
            key = (item.get("id") or item.get("title") or item.get("content") or str(item))[:200]

            if key in seen:
                continue

            # Score complexity
            content = json.dumps(item)
            score = compute_score(content)

            # Delegate if complex (score ≥7)
            if score >= 7:
                prompt = rewrite_for_auggie(content)
                perform_delegation(prompt)
                seen.add(key)
                delegated += 1

        return delegated
    except Exception as e:
        print(f"Error processing todos: {e}", file=sys.stderr)
        return 0


def run_daemon() -> None:
    """Main daemon loop - poll todos and delegate complex work."""
    if not _write_pidfile():
        return

    seen: set = set()

    try:
        while True:
            process_todos_once(TODO_PATH, seen)
            time.sleep(POLL_SECONDS)
    finally:
        # Cleanup PID file on exit
        if PID_FILE.exists():
            PID_FILE.unlink()


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        run_daemon()
    else:
        print("Usage: delegation_watcher.py --daemon", file=sys.stderr)
        sys.exit(1)
