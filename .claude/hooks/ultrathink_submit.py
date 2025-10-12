#!/usr/bin/env python3
"""
UserPromptSubmit hook to enforce deep thinking (ultrathink) on every prompt.
- Prints a short directive to stdout; Claude Code prepends this before the user's prompt.
- Set ULTRATHINK_DISABLE=1 in environment to temporarily disable.
- Include phrase "no-ultrathink" in your prompt to skip for a single message.
"""
import os
import sys

# Allow global toggle via env var
if os.getenv("ULTRATHINK_DISABLE") == "1":
    sys.exit(0)

# Best-effort single-message opt-out if user types "no-ultrathink"
try:
    raw = sys.stdin.read()
    if "no-ultrathink" in (raw or "").lower():
        sys.exit(0)
except Exception:
    pass

preamble = (
    "ultrathink\n"
    "Think step by step before responding. Plan first, then act. "
    "Challenge your first idea, list key assumptions, and be explicit about trade-offs. "
    "Return sections: Plan, Code, Tests, and a brief Critique."
)
print(preamble)

