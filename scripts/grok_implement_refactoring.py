#!/usr/bin/env python3
"""
Interactive Grok session that autonomously implements refactoring recommendations.
Grok can read, edit, create files, run tests, and verify changes.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Any, Dict

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.grok_session import GrokSession


# Define tools for Grok to use
IMPLEMENTATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the complete contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file relative to project root (e.g., 'src/main.py')"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edit a file by replacing old_string with new_string. Must match exactly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file to edit"
                    },
                    "old_string": {
                        "type": "string",
                        "description": "Exact string to replace (must match exactly including whitespace)"
                    },
                    "new_string": {
                        "type": "string",
                        "description": "New string to replace with"
                    }
                },
                "required": ["file_path", "old_string", "new_string"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Run the test suite to verify changes",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_path": {
                        "type": "string",
                        "description": "Optional: Specific test file or directory (default: 'tests/')"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Show git diff of current changes",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Optional: Specific file to diff (default: all changes)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory path"
                    }
                },
                "required": ["directory"]
            }
        }
    }
]


def read_file(file_path: str) -> str:
    """Read a file and return numbered contents."""
    project_root = Path(__file__).parent.parent
    full_path = project_root / file_path

    if not full_path.exists():
        return f"Error: File not found: {file_path}"

    try:
        content = full_path.read_text()
        lines = content.split('\n')
        numbered = '\n'.join(f"{i+1:4d}: {line}" for i, line in enumerate(lines))
        return f"=== {file_path} ===\n\n{numbered}"
    except Exception as e:
        return f"Error reading {file_path}: {str(e)}"


def edit_file(file_path: str, old_string: str, new_string: str) -> str:
    """Edit a file by replacing old_string with new_string."""
    project_root = Path(__file__).parent.parent
    full_path = project_root / file_path

    if not full_path.exists():
        return f"Error: File not found: {file_path}"

    try:
        content = full_path.read_text()

        if old_string not in content:
            return f"Error: old_string not found in {file_path}. Make sure it matches exactly including whitespace."

        # Count occurrences
        count = content.count(old_string)
        if count > 1:
            return f"Error: old_string appears {count} times in {file_path}. Make it more specific to match only once."

        # Make the replacement
        new_content = content.replace(old_string, new_string)
        full_path.write_text(new_content)

        return f"Success: Edited {file_path}\n- Replaced {len(old_string)} chars with {len(new_string)} chars\n- File updated successfully"

    except Exception as e:
        return f"Error editing {file_path}: {str(e)}"


def run_tests(test_path: str = "tests/") -> str:
    """Run tests and return results."""
    project_root = Path(__file__).parent.parent

    try:
        # Run pytest
        result = subprocess.run(
            ["pytest", test_path, "-v", "--tb=short"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "PYTHONPATH": str(project_root)}
        )

        output = result.stdout + result.stderr

        # Summarize results
        if result.returncode == 0:
            summary = f"✅ ALL TESTS PASSED\n\n{output[-500:]}"  # Last 500 chars
        else:
            summary = f"❌ TESTS FAILED\n\n{output[-1000:]}"  # Last 1000 chars for errors

        return summary

    except subprocess.TimeoutExpired:
        return "Error: Tests timed out after 120 seconds"
    except Exception as e:
        return f"Error running tests: {str(e)}"


def git_diff(file_path: str = None) -> str:
    """Show git diff."""
    project_root = Path(__file__).parent.parent

    try:
        cmd = ["git", "diff"]
        if file_path:
            cmd.append(file_path)

        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30
        )

        if not result.stdout:
            return "No changes detected"

        # Limit output
        diff = result.stdout
        if len(diff) > 2000:
            diff = diff[:2000] + "\n\n... (diff truncated, too long)"

        return f"=== Git Diff ===\n\n{diff}"

    except Exception as e:
        return f"Error getting diff: {str(e)}"


def list_directory(directory: str) -> str:
    """List directory contents."""
    project_root = Path(__file__).parent.parent
    dir_path = project_root / directory

    if not dir_path.exists():
        return f"Error: Directory not found: {directory}"

    try:
        items = []
        for item in sorted(dir_path.iterdir()):
            prefix = "[DIR] " if item.is_dir() else "[FILE]"
            items.append(f"{prefix} {item.name}")

        return f"=== {directory}/ ===\n\n" + '\n'.join(items)
    except Exception as e:
        return f"Error listing {directory}: {str(e)}"


def run_implementation():
    """Run autonomous implementation with Grok."""
    print("=" * 80)
    print("GROK AUTONOMOUS REFACTORING IMPLEMENTATION")
    print("=" * 80)
    print()
    print("Grok will implement the refactoring recommendations from the investigation.")
    print()
    print("Available tools:")
    for tool in IMPLEMENTATION_TOOLS:
        print(f"  - {tool['function']['name']}: {tool['function']['description']}")
    print()
    print("⚠️  WARNING: Grok will make real changes to code files!")
    print()

    # Confirm
    response = input("Continue with autonomous implementation? (yes/no): ").strip().lower()
    if response != "yes":
        print("Aborted.")
        return None

    print()
    print("=" * 80)
    print()

    # Initialize session
    session = GrokSession(
        model="grok-code-fast-1",
        system_prompt="""You are Grok, an expert software engineer implementing Clean Architecture refactorings.

You have tools to read, edit files, run tests, and check diffs.

**Your Mission:**
Implement the 6 refactoring recommendations from docs/grok_refactoring_investigation.md

**Implementation Strategy:**
1. Start with HIGH priority items
2. For each change:
   - Read the relevant file
   - Make the edit carefully (old_string must match EXACTLY)
   - Run tests to verify
   - Check git diff to confirm changes
3. Move to next recommendation only if tests pass
4. If tests fail, debug and fix before continuing

**Critical Rules:**
- Make ONE change at a time
- ALWAYS run tests after each change
- old_string must match EXACTLY (including indentation, line breaks)
- If edit fails, read the file again and try with exact match
- Stop if tests fail and you can't fix

**Implementation Order:**
1. HIGH: Implement LLM response parsing (task_planner.py)
2. HIGH: Refine agent selection (agent.py)
3. MEDIUM: Normalize ProviderFactory (provider_factory.py)
4. MEDIUM: Delete deprecated coordinator.py
5. LOW: Extract display logic (main.py)
6. LOW: Skip CLI adapters for now

Be methodical. Test after EVERY change."""
    )

    # Set tools
    session.tools = IMPLEMENTATION_TOOLS
    session.tool_functions = {
        "read_file": read_file,
        "edit_file": edit_file,
        "run_tests": run_tests,
        "git_diff": git_diff,
        "list_directory": list_directory
    }

    # Implementation prompt
    implementation_prompt = """# Refactoring Implementation Task

Implement the refactoring recommendations from your investigation.

## Reference Document

Read docs/grok_refactoring_investigation.md for full context.

## Implementation Checklist

### HIGH PRIORITY
1. ✅ Implement LLM response parsing in src/use_cases/task_planner.py
   - Add JSON parsing in _parse_llm_response method
   - Import json module
   - Add try/except for parsing errors

2. ✅ Refine agent selection in src/entities/agent.py
   - Replace substring matching with difflib.SequenceMatcher
   - Import difflib
   - Set threshold to 0.8

### MEDIUM PRIORITY
3. ✅ Normalize ProviderFactory in src/factories/provider_factory.py
   - Remove if-elif special-casing for Grok
   - Register Grok in __init__
   - Use uniform creation logic

4. ✅ Delete deprecated src/use_cases/coordinator.py
   - Remove the entire file
   - Verify no imports reference it

### LOW PRIORITY
5. ✅ Extract display logic helpers (optional)
6. ⏭️  Skip CLI adapters

## Instructions

Start with HIGH priority item #1. For each change:
1. read_file to see current code
2. edit_file to make the change
3. run_tests to verify
4. git_diff to confirm changes

Work methodically. Test after EVERY change.

**BEGIN IMPLEMENTATION NOW.**"""

    print("Sending implementation task to Grok...")
    print("(Grok will autonomously implement all recommendations)")
    print()
    print("=" * 80)
    print()

    # Run implementation
    result = session.send_message(implementation_prompt)

    # Track changes
    all_tool_calls = []
    if result['tool_results']:
        all_tool_calls.extend(result['tool_results'])

    # Display first round
    round_num = 1
    if result['tool_results']:
        print(f"ROUND {round_num}: Grok used {len(result['tool_results'])} tools")
        for i, tool_result in enumerate(result['tool_results'], 1):
            tool_name = tool_result['tool']
            args = tool_result.get('args', {})
            print(f"  {i}. {tool_name}({json.dumps(args, indent=2)})")
        print()

    # Continue until done
    max_rounds = 25  # More rounds for implementation
    while result['tool_results'] and round_num < max_rounds:
        round_num += 1

        follow_up = """Continue implementing the next refactoring recommendation.

Remember:
- Make ONE change at a time
- Run tests after EACH change
- Check git diff to verify
- If tests fail, fix before continuing
- Provide status update when all recommendations are implemented"""

        result = session.send_message(follow_up)

        if result['tool_results']:
            all_tool_calls.extend(result['tool_results'])
            print(f"ROUND {round_num}: Grok used {len(result['tool_results'])} tools")
            for i, tool_result in enumerate(result['tool_results'], 1):
                tool_name = tool_result['tool']
                args = tool_result.get('args', {})

                # Show brief summary for edits
                if tool_name == "edit_file":
                    file_path = args.get('file_path', 'unknown')
                    print(f"  {i}. edit_file('{file_path}')")
                else:
                    print(f"  {i}. {tool_name}({json.dumps(args)})")
            print()

    # Final status
    if round_num >= max_rounds:
        print(f"\nReached maximum rounds ({max_rounds}).")
    else:
        print(f"\nImplementation complete after {round_num} rounds.")

    print()
    print("=" * 80)
    print("GROK'S FINAL STATUS")
    print("=" * 80)
    print()
    print(result['response'])
    print()
    print("=" * 80)
    print()

    # Save implementation log
    output_file = Path("docs/grok_implementation_log.md")
    with open(output_file, 'w') as f:
        f.write("# Grok's Autonomous Implementation Log\n\n")
        f.write("## Session Summary\n\n")
        f.write(f"- Model: grok-code-fast-1\n")
        f.write(f"- Implementation rounds: {round_num}\n")
        f.write(f"- Total tool calls: {len(all_tool_calls)}\n")
        f.write(f"- Success: {result['success']}\n\n")

        # Count tool types
        tool_counts = {}
        for tc in all_tool_calls:
            tool = tc['tool']
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

        f.write("## Tools Used\n\n")
        for tool, count in sorted(tool_counts.items()):
            f.write(f"- {tool}: {count} calls\n")
        f.write("\n")

        f.write("## Implementation Status\n\n")
        f.write(result['response'])

    print(f"Implementation log saved to: {output_file}")
    print()

    # Show final diff
    print("=" * 80)
    print("FINAL CHANGES")
    print("=" * 80)
    print()
    final_diff = git_diff()
    print(final_diff)
    print()

    return result


if __name__ == "__main__":
    try:
        run_implementation()
    except KeyboardInterrupt:
        print("\n\nImplementation interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)