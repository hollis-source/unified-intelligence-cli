#!/usr/bin/env python3
"""
Test Agent Modes - Integration test for default vs extended agent modes.

Week 11 Phase 1: Validate CLI integration works with both 5 and 8 agent modes.
"""

import subprocess
import sys
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'
BOLD = '\033[1m'

def run_cli(task: str, agent_mode: str) -> tuple:
    """
    Run CLI command and return (success, output).

    Args:
        task: Task description
        agent_mode: "default" or "extended"

    Returns:
        (success: bool, output: str)
    """
    cmd = [
        "venv/bin/python3", "-m", "src.main",
        "--task", task,
        "--provider", "mock",
        "--agents", agent_mode,
        "--verbose"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent
        )
        success = result.returncode == 0
        output = result.stdout + result.stderr
        return success, output
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)


def test_agent_mode(mode: str, expected_agent_count: int) -> bool:
    """Test a specific agent mode."""

    print(f"\n{BOLD}Testing {mode.upper()} mode ({expected_agent_count} agents){RESET}")
    print("="*60)

    test_tasks = [
        "Write a Python function to add two numbers",
        "Design a REST API for user management",
        "Plan the project architecture"
    ]

    all_passed = True

    for i, task in enumerate(test_tasks, 1):
        print(f"\n{i}. Task: \"{task[:50]}...\"")

        success, output = run_cli(task, mode)

        if not success:
            print(f"   {RED}❌ FAILED{RESET} - CLI execution failed")
            all_passed = False
            continue

        # Check for expected agent count
        agent_count_str = f"Created {expected_agent_count} agents"
        if agent_count_str in output:
            print(f"   {GREEN}✅ PASSED{RESET} - Correct agent count ({expected_agent_count})")
        else:
            print(f"   {RED}❌ FAILED{RESET} - Agent count mismatch")
            all_passed = False
            continue

        # Check for mode indicator
        if mode == "extended" and "extended mode" in output:
            print(f"   {GREEN}✅ PASSED{RESET} - Extended mode confirmed")
        elif mode == "default" and "default mode" in output:
            print(f"   {GREEN}✅ PASSED{RESET} - Default mode confirmed")
        else:
            print(f"   {RED}❌ FAILED{RESET} - Mode indicator not found")
            all_passed = False
            continue

        # Check for successful task completion
        if "status: success" in output.lower() or "completed" in output.lower():
            print(f"   {GREEN}✅ PASSED{RESET} - Task completed successfully")
        else:
            print(f"   {RED}⚠️ WARNING{RESET} - Task completion unclear (mock provider)")

    return all_passed


def main():
    """Run agent mode integration tests."""

    print(f"{BOLD}{'='*60}")
    print("AGENT MODE INTEGRATION TEST")
    print(f"{'='*60}{RESET}")

    # Test default mode (5 agents)
    default_passed = test_agent_mode("default", 5)

    # Test extended mode (8 agents)
    extended_passed = test_agent_mode("extended", 8)

    # Summary
    print(f"\n{BOLD}{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}{RESET}")

    print(f"\nDefault Mode (5 agents):  {'✅ PASSED' if default_passed else '❌ FAILED'}")
    print(f"Extended Mode (8 agents): {'✅ PASSED' if extended_passed else '❌ FAILED'}")

    all_passed = default_passed and extended_passed

    print(f"\n{BOLD}{'='*60}")
    if all_passed:
        print(f"{GREEN}✅ ALL TESTS PASSED{RESET}")
    else:
        print(f"{RED}❌ SOME TESTS FAILED{RESET}")
    print(f"{'='*60}{BOLD}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
