#!/usr/bin/env python3
"""
Interactive Grok session with IMPROVED editing tools for autonomous implementation.
Uses line-based editing instead of exact string matching for easier modifications.
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


# Define improved tools for Grok
IMPLEMENTATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read complete file contents with line numbers",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file relative to project root"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_lines",
            "description": "Read specific line range from a file (easier for targeting specific functions/methods)",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file"
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Starting line number (1-indexed)"
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Ending line number (inclusive)"
                    }
                },
                "required": ["file_path", "start_line", "end_line"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "replace_lines",
            "description": "Replace lines in a file by line number range (NO EXACT MATCHING NEEDED - just specify line numbers and new content)",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file"
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Starting line number to replace (1-indexed)"
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Ending line number to replace (inclusive)"
                    },
                    "new_content": {
                        "type": "string",
                        "description": "New content to replace with (can be multiple lines)"
                    }
                },
                "required": ["file_path", "start_line", "end_line", "new_content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "insert_lines",
            "description": "Insert new lines at a specific position",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file"
                    },
                    "after_line": {
                        "type": "integer",
                        "description": "Insert after this line number (0 = insert at beginning)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to insert"
                    }
                },
                "required": ["file_path", "after_line", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file completely",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file to delete"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Run test suite to verify changes",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_path": {
                        "type": "string",
                        "description": "Optional: Specific test file (default: all tests)"
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
            "description": "Show git diff of changes",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Optional: Specific file (default: all)"
                    }
                },
                "required": []
            }
        }
    }
]


def read_file(file_path: str) -> str:
    """Read file with line numbers."""
    project_root = Path(__file__).parent.parent
    full_path = project_root / file_path

    if not full_path.exists():
        return f"Error: File not found: {file_path}"

    try:
        content = full_path.read_text()
        lines = content.split('\n')
        numbered = '\n'.join(f"{i+1:4d}: {line}" for i, line in enumerate(lines))
        return f"=== {file_path} ({len(lines)} lines) ===\n\n{numbered}"
    except Exception as e:
        return f"Error reading {file_path}: {str(e)}"


def read_lines(file_path: str, start_line: int, end_line: int) -> str:
    """Read specific line range."""
    project_root = Path(__file__).parent.parent
    full_path = project_root / file_path

    if not full_path.exists():
        return f"Error: File not found: {file_path}"

    try:
        lines = full_path.read_text().split('\n')

        # Convert to 0-indexed
        start_idx = start_line - 1
        end_idx = end_line  # end is inclusive

        if start_idx < 0 or end_idx > len(lines):
            return f"Error: Line range {start_line}-{end_line} out of bounds (file has {len(lines)} lines)"

        selected = lines[start_idx:end_idx]
        numbered = '\n'.join(f"{i+start_line:4d}: {line}" for i, line in enumerate(selected))

        return f"=== {file_path} lines {start_line}-{end_line} ===\n\n{numbered}"
    except Exception as e:
        return f"Error reading lines: {str(e)}"


def replace_lines(file_path: str, start_line: int, end_line: int, new_content: str) -> str:
    """Replace lines by line number - NO EXACT MATCHING NEEDED!"""
    project_root = Path(__file__).parent.parent
    full_path = project_root / file_path

    if not full_path.exists():
        return f"Error: File not found: {file_path}"

    try:
        lines = full_path.read_text().split('\n')

        # Convert to 0-indexed
        start_idx = start_line - 1
        end_idx = end_line  # end is inclusive

        if start_idx < 0 or end_idx > len(lines):
            return f"Error: Line range {start_line}-{end_line} out of bounds (file has {len(lines)} lines)"

        # Split new content into lines
        new_lines = new_content.split('\n')

        # Replace the range
        lines[start_idx:end_idx] = new_lines

        # Write back
        full_path.write_text('\n'.join(lines))

        return f"Success: Replaced lines {start_line}-{end_line} in {file_path}\n- Old: {end_line - start_line + 1} lines\n- New: {len(new_lines)} lines"

    except Exception as e:
        return f"Error replacing lines: {str(e)}"


def insert_lines(file_path: str, after_line: int, content: str) -> str:
    """Insert lines after specified line."""
    project_root = Path(__file__).parent.parent
    full_path = project_root / file_path

    if not full_path.exists():
        return f"Error: File not found: {file_path}"

    try:
        lines = full_path.read_text().split('\n')

        if after_line < 0 or after_line > len(lines):
            return f"Error: Line {after_line} out of bounds (file has {len(lines)} lines)"

        # Split content
        new_lines = content.split('\n')

        # Insert
        lines[after_line:after_line] = new_lines

        # Write back
        full_path.write_text('\n'.join(lines))

        return f"Success: Inserted {len(new_lines)} lines after line {after_line} in {file_path}"

    except Exception as e:
        return f"Error inserting lines: {str(e)}"


def delete_file(file_path: str) -> str:
    """Delete a file."""
    project_root = Path(__file__).parent.parent
    full_path = project_root / file_path

    if not full_path.exists():
        return f"Error: File not found: {file_path}"

    try:
        full_path.unlink()
        return f"Success: Deleted {file_path}"
    except Exception as e:
        return f"Error deleting {file_path}: {str(e)}"


def run_tests(test_path: str = "tests/") -> str:
    """Run tests."""
    project_root = Path(__file__).parent.parent

    try:
        result = subprocess.run(
            ["pytest", test_path, "-v", "--tb=short"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "PYTHONPATH": str(project_root)}
        )

        output = result.stdout + result.stderr

        if result.returncode == 0:
            # Extract summary line
            summary_lines = [line for line in output.split('\n') if 'passed' in line]
            if summary_lines:
                return f"✅ TESTS PASSED\n\n{summary_lines[-1]}"
            return f"✅ TESTS PASSED\n\n{output[-300:]}"
        else:
            return f"❌ TESTS FAILED\n\n{output[-1500:]}"

    except subprocess.TimeoutExpired:
        return "Error: Tests timed out after 120 seconds"
    except Exception as e:
        return f"Error running tests: {str(e)}"


def git_diff(file_path: str = None) -> str:
    """Show git diff."""
    project_root = Path(__file__).parent.parent

    try:
        cmd = ["git", "diff", "--stat"] if not file_path else ["git", "diff", file_path]

        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30
        )

        if not result.stdout:
            return "No changes detected"

        return f"=== Git Diff ===\n\n{result.stdout}"

    except Exception as e:
        return f"Error getting diff: {str(e)}"


def run_implementation():
    """Run autonomous implementation with improved tools."""
    print("=" * 80)
    print("GROK AUTONOMOUS REFACTORING (v2 - IMPROVED LINE-BASED EDITING)")
    print("=" * 80)
    print()
    print("Improved editing capabilities:")
    print("  ✓ replace_lines - Replace by line number (no exact matching!)")
    print("  ✓ read_lines - Inspect specific line ranges")
    print("  ✓ insert_lines - Insert at specific positions")
    print("  ✓ delete_file - Remove files")
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
        system_prompt="""You are Grok, an expert software engineer implementing refactorings.

You have IMPROVED editing tools that use LINE NUMBERS instead of exact string matching!

**Available Tools:**
- read_file: Read entire file with line numbers
- read_lines(file, start, end): Read specific lines
- replace_lines(file, start, end, new_content): Replace lines by number - EASY!
- insert_lines(file, after_line, content): Insert at position
- delete_file: Delete entire file
- run_tests: Verify changes
- git_diff: Check changes

**Workflow for Each Change:**
1. read_file or read_lines to see current code
2. Identify line numbers for the section to change
3. Use replace_lines with line numbers - NO EXACT MATCHING NEEDED!
4. run_tests to verify
5. git_diff to confirm

**Example:**
To replace a method at lines 50-65:
1. read_lines(file, 50, 65) to see it
2. replace_lines(file, 50, 65, "new method implementation")
3. run_tests()

**Your Mission:**
Continue implementing remaining recommendations from docs/grok_refactoring_investigation.md

**Status of Previous Attempt:**
✅ json import added to task_planner.py
✅ difflib import added to agent.py
❌ Actual logic NOT yet implemented

**TODO:**
1. HIGH: Implement JSON parsing logic in task_planner.py _parse_llm_response method
2. HIGH: Implement difflib logic in agent.py can_handle method
3. MEDIUM: Normalize ProviderFactory
4. MEDIUM: Delete deprecated coordinator.py

Work methodically. Test after EACH change."""
    )

    # Set tools
    session.tools = IMPLEMENTATION_TOOLS
    session.tool_functions = {
        "read_file": read_file,
        "read_lines": read_lines,
        "replace_lines": replace_lines,
        "insert_lines": insert_lines,
        "delete_file": delete_file,
        "run_tests": run_tests,
        "git_diff": git_diff
    }

    # Implementation prompt
    implementation_prompt = """# Continue Refactoring Implementation

Previous attempt added imports but not the actual logic. Complete the implementation now.

## Current Status

Check what's already done:
- git_diff() to see current changes

## TODO

### HIGH PRIORITY (start here)

1. **Implement JSON parsing in task_planner.py**
   - read_file("src/use_cases/task_planner.py")
   - Find _parse_llm_response method (around line 108-133)
   - Replace it to add JSON parsing logic
   - Use replace_lines() with line numbers

2. **Implement difflib in agent.py**
   - read_file("src/entities/agent.py")
   - Find can_handle method (around line 14-18)
   - Replace to use SequenceMatcher
   - Use replace_lines()

### MEDIUM PRIORITY

3. **Normalize ProviderFactory**
   - read_file("src/factories/provider_factory.py")
   - Replace create_provider method to remove if-elif

4. **Delete coordinator.py**
   - delete_file("src/use_cases/coordinator.py")

Test after EVERY change!

**BEGIN with HIGH priority item #1 now.**"""

    print("Sending implementation task to Grok...")
    print()
    print("=" * 80)
    print()

    # Run
    result = session.send_message(implementation_prompt)

    # Track
    all_tool_calls = []
    if result['tool_results']:
        all_tool_calls.extend(result['tool_results'])

    # Display
    round_num = 1
    if result['tool_results']:
        print(f"ROUND {round_num}: Grok used {len(result['tool_results'])} tools")
        for i, tool_result in enumerate(result['tool_results'], 1):
            tool_name = tool_result['tool']
            args = tool_result.get('args', {})
            if tool_name == "replace_lines":
                file = args.get('file_path', '?')
                start = args.get('start_line', '?')
                end = args.get('end_line', '?')
                print(f"  {i}. replace_lines('{file}', {start}-{end})")
            else:
                print(f"  {i}. {tool_name}({json.dumps(args)})")
        print()

    # Continue
    max_rounds = 25
    while result['tool_results'] and round_num < max_rounds:
        round_num += 1

        follow_up = """Continue with next recommendation.

After each change:
1. run_tests() to verify
2. If tests pass, move to next item
3. If tests fail, fix it before continuing"""

        result = session.send_message(follow_up)

        if result['tool_results']:
            all_tool_calls.extend(result['tool_results'])
            print(f"ROUND {round_num}: Grok used {len(result['tool_results'])} tools")
            for i, tool_result in enumerate(result['tool_results'], 1):
                tool_name = tool_result['tool']
                args = tool_result.get('args', {})
                if tool_name == "replace_lines":
                    file = args.get('file_path', '?')
                    start = args.get('start_line', '?')
                    end = args.get('end_line', '?')
                    print(f"  {i}. replace_lines('{file}', {start}-{end})")
                else:
                    print(f"  {i}. {tool_name}({json.dumps(args)})")
            print()

    # Final status
    print()
    print("=" * 80)
    print("IMPLEMENTATION COMPLETE")
    print("=" * 80)
    print()
    print(result['response'])
    print()

    # Save log
    output_file = Path("docs/grok_implementation_v2_log.md")
    with open(output_file, 'w') as f:
        f.write("# Grok Implementation Log (v2 - Line-Based Editing)\n\n")
        f.write(f"- Rounds: {round_num}\n")
        f.write(f"- Tool calls: {len(all_tool_calls)}\n\n")
        f.write("## Status\n\n")
        f.write(result['response'])

    print(f"Log saved to: {output_file}")
    print()

    # Show changes
    print("=" * 80)
    print("FINAL CHANGES")
    print("=" * 80)
    subprocess.run(["git", "diff", "--stat"], cwd=Path(__file__).parent.parent)
    print()

    return result


if __name__ == "__main__":
    try:
        run_implementation()
    except KeyboardInterrupt:
        print("\n\nInterrupted.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)