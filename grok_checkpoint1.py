#!/usr/bin/env python3
"""
Grok Checkpoint 1 - Verify Progress on Recommendations

Quick verification of implemented recommendations.
"""

import os
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))

from grok_session import GrokSession


def run_command(cmd):
    """Run command and return output."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, timeout=30
    )
    return result.stdout if result.stdout else result.stderr


def main():
    """Run Grok checkpoint verification."""

    print("=" * 80)
    print("GROK CHECKPOINT #1 - PROGRESS VERIFICATION")
    print("=" * 80)
    print()

    if not os.getenv("XAI_API_KEY"):
        print("❌ Error: XAI_API_KEY not set")
        return 1

    print("📊 Gathering progress data...")
    print()

    # Get coverage
    coverage = run_command(
        "cd /home/ui-cli_jake/unified-intelligence-cli && . venv/bin/activate && "
        "python3 -c \"import sys; sys.path.insert(0, '.'); import pytest; "
        "pytest.main(['tests/', '--cov=src', '--cov-report=term'])\" 2>&1 | "
        "grep -A 2 'TOTAL'"
    )

    # Get test count
    test_count = run_command(
        "cd /home/ui-cli_jake/unified-intelligence-cli && . venv/bin/activate && "
        "python3 -c \"import sys; sys.path.insert(0, '.'); import pytest; "
        "pytest.main(['-v', 'tests/'])\" 2>&1 | grep 'passed'"
    )

    # Get recent commits
    commits = run_command("git log --oneline -5")

    # List new files
    new_files = run_command("git diff --name-only cdc6c32..HEAD")

    print("✓ Data collected")
    print()

    # Create Grok session
    print("🤖 Initializing Grok verification...")
    session = GrokSession(model="grok-code-fast-1", enable_logging=True)

    system_msg = """You are an expert code reviewer. Verify progress on previous recommendations concisely."""

    session.messages.append({"role": "system", "content": system_msg})

    review_request = f"""Quick checkpoint: Verify progress on your recommendations from the previous review.

## PROGRESS SUMMARY

**Previous Review:** GROK_CODE_REVIEW.md recommended 7 improvements

**Implemented So Far:**

1. ✅ **Increase Coverage (Rec #1):**
   - Added 19 unit tests for main.py and composition.py
   - Coverage: 65-70% → 79% (+9-14pp)
   - main.py: 0% → 76%
   - composition.py: 0% → 100%

2. ✅ **Custom Exceptions (Rec #3):**
   - Created src/exceptions.py with 7 exception types
   - Added 17 comprehensive exception tests
   - Updated tools.py to raise exceptions

**Test Results:**
{test_count}

**Coverage:**
{coverage}

**Recent Commits:**
{commits}

**New Files:**
{new_files}

## VERIFICATION REQUEST

Please verify:
1. Are we on track toward 80% coverage goal?
2. Is the custom exception implementation sound?
3. What should be prioritized next from remaining recommendations?

Keep response concise (3-4 paragraphs max)."""

    print("📤 Sending checkpoint request...")
    print()

    result = session.send_message(
        user_message=review_request,
        temperature=0.3,
        use_tools=False
    )

    print("=" * 80)
    print("GROK CHECKPOINT VERIFICATION")
    print("=" * 80)
    print()
    print(result["response"])
    print()

    # Save checkpoint
    output_file = Path("GROK_CHECKPOINT_1.md")
    with open(output_file, 'w') as f:
        f.write("# Grok Checkpoint #1 - Progress Verification\n\n")
        f.write("**Date:** 2025-09-30\n")
        f.write("**Recommendations Addressed:** 2/7\n\n")
        f.write("---\n\n")
        f.write(result["response"])

    print(f"✓ Checkpoint saved to {output_file}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())