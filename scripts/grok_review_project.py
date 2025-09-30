#!/usr/bin/env python3
"""
Interactive Grok Project Review - Generate Todos
Uses grok-4-0709 to review project state and suggest next steps.
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.grok_session import GrokSession

# ============================================================================
# INVESTIGATION TOOLS
# ============================================================================

def read_file(file_path: str) -> str:
    """Read contents of a file."""
    try:
        full_path = project_root / file_path
        if not full_path.exists():
            return f"Error: File not found: {file_path}"

        content = full_path.read_text()
        lines = content.split('\n')

        # Add line numbers for reference
        numbered = '\n'.join(f"{i+1:4d} | {line}" for i, line in enumerate(lines))
        return f"File: {file_path}\n{numbered}"
    except Exception as e:
        return f"Error reading {file_path}: {str(e)}"


def list_directory(dir_path: str = ".") -> str:
    """List contents of a directory."""
    try:
        full_path = project_root / dir_path
        if not full_path.exists():
            return f"Error: Directory not found: {dir_path}"

        items = []
        for item in sorted(full_path.iterdir()):
            if item.name.startswith('.'):
                continue

            item_type = "DIR" if item.is_dir() else "FILE"
            size = item.stat().st_size if item.is_file() else "-"
            items.append(f"{item_type:5} {size:>10} {item.name}")

        return f"Directory: {dir_path}\n" + '\n'.join(items)
    except Exception as e:
        return f"Error listing {dir_path}: {str(e)}"


def search_code(pattern: str, file_pattern: str = "*.py") -> str:
    """Search for pattern in code files."""
    try:
        import subprocess
        result = subprocess.run(
            ['grep', '-r', '-n', '--include', file_pattern, pattern, str(project_root / 'src')],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[:20]  # Limit to 20 matches
            return f"Found {len(lines)} matches:\n" + '\n'.join(lines)
        else:
            return f"No matches found for pattern: {pattern}"
    except Exception as e:
        return f"Error searching: {str(e)}"


def count_lines(file_path: str) -> str:
    """Count lines in a file."""
    try:
        full_path = project_root / file_path
        if not full_path.exists():
            return f"Error: File not found: {file_path}"

        content = full_path.read_text()
        lines = content.split('\n')
        total = len(lines)
        non_empty = sum(1 for line in lines if line.strip())

        return f"{file_path}: {total} total lines, {non_empty} non-empty"
    except Exception as e:
        return f"Error: {str(e)}"


def read_git_log(count: int = 10) -> str:
    """Read recent git commits."""
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'log', f'-{count}', '--oneline', '--decorate'],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            return f"Recent commits:\n{result.stdout}"
        else:
            return "Error reading git log"
    except Exception as e:
        return f"Error: {str(e)}"


def read_git_status() -> str:
    """Read current git status."""
    try:
        import subprocess
        result = subprocess.run(
            ['git', 'status', '--short'],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            return f"Git status:\n{result.stdout}" if result.stdout else "Working tree clean"
        else:
            return "Error reading git status"
    except Exception as e:
        return f"Error: {str(e)}"


def run_tests() -> str:
    """Run the test suite."""
    try:
        import subprocess
        result = subprocess.run(
            ['pytest', 'tests/', '-v', '--tb=short'],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Extract summary line
        output_lines = result.stdout.split('\n')
        summary = [line for line in output_lines if 'passed' in line or 'failed' in line]

        return f"Test results:\n" + '\n'.join(summary[-3:]) if summary else result.stdout[-500:]
    except Exception as e:
        return f"Error running tests: {str(e)}"


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

INVESTIGATION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file with line numbers",
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
            "name": "list_directory",
            "description": "List contents of a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "dir_path": {
                        "type": "string",
                        "description": "Path to directory (default: project root)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for a pattern in code files",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Pattern to search for"
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "File pattern (default: *.py)"
                    }
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "count_lines",
            "description": "Count total and non-empty lines in a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to file"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_git_log",
            "description": "Read recent git commit history",
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of commits to show (default: 10)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_git_status",
            "description": "Read current git working tree status",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Run the test suite and return summary",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


# ============================================================================
# MAIN
# ============================================================================

def run_interactive_review():
    """Run interactive project review with Grok."""

    print("=" * 80)
    print("GROK PROJECT REVIEW - TODO GENERATION")
    print("=" * 80)
    print()
    print("Using model: grok-4-0709")
    print("Tools available:")
    for tool in INVESTIGATION_TOOLS:
        print(f"  ✓ {tool['function']['name']}")
    print()

    # Initialize session
    session = GrokSession(
        model="grok-4-0709",
        system_prompt="""You are Grok, an expert software architect and project manager.

Your task is to review the Unified Intelligence CLI project and suggest actionable next steps.

**Project Context:**
- A CLI tool for multi-agent AI systems
- Built with Clean Architecture principles
- Uses SOLID design patterns
- Integrates with Grok API and other LLM providers
- Python-based with pytest for testing

**Your Review Process:**
1. Explore the project structure (list directories, read key files)
2. Review recent commit history to understand what's been done
3. Check test coverage and code quality
4. Identify what's implemented vs. what's missing
5. Review documentation (README, CLAUDE.md, etc.)
6. Analyze architecture for missing components
7. Check for TODOs in code
8. Review interfaces vs. implementations

**Output Format:**
After thorough investigation, provide a prioritized list of todos in this format:

## HIGH PRIORITY
1. [Category] Task description (file:line if specific)
   - Why: Rationale
   - Impact: What this enables

2. ...

## MEDIUM PRIORITY
...

## LOW PRIORITY
...

Be specific, actionable, and evidence-based. Reference actual files and line numbers.
Use your tools extensively before making suggestions."""
    )

    # Set up tools
    session.tools = INVESTIGATION_TOOLS
    session.tool_functions = {
        "read_file": read_file,
        "list_directory": list_directory,
        "search_code": search_code,
        "count_lines": count_lines,
        "read_git_log": read_git_log,
        "read_git_status": read_git_status,
        "run_tests": run_tests
    }

    # Initial investigation prompt
    investigation_prompt = """Review the Unified Intelligence CLI project and suggest prioritized todos.

Start by exploring:
1. Project structure (src/, tests/, docs/)
2. Recent git commits
3. Current test status
4. Key architecture files
5. Missing implementations
6. Documentation gaps

Take your time to thoroughly investigate before making suggestions."""

    print("Sending review task to Grok...")
    print("=" * 80)
    print()

    result = session.send_message(investigation_prompt)

    # Iterative investigation
    round_num = 1
    max_rounds = 20

    while result['tool_results'] and round_num < max_rounds:
        print(f"\nROUND {round_num}: Grok used {len(result['tool_results'])} tools")
        for i, tool_result in enumerate(result['tool_results'], 1):
            tool_name = tool_result.get('tool', 'unknown')
            args = tool_result.get('args', {})
            print(f"  {i}. {tool_name}({args})")

        round_num += 1

        # Continue investigation
        follow_up = "Continue your investigation. Use more tools if needed, or provide your final recommendations."
        result = session.send_message(follow_up)

    # Final response
    print("\n" + "=" * 80)
    print("REVIEW COMPLETE")
    print("=" * 80)
    print()

    final_text = result.get('response', '')
    print(final_text)

    # Save to file
    output_file = project_root / "docs" / "grok_project_todos.md"
    output_file.write_text(f"""# Grok Project Review - TODO Suggestions

**Model:** grok-4-0709
**Date:** {os.popen('date').read().strip()}
**Rounds:** {round_num}

---

{final_text}
""")

    print("\n" + "=" * 80)
    print(f"Recommendations saved to: {output_file.relative_to(project_root)}")
    print("=" * 80)


if __name__ == "__main__":
    # Check for API key
    if not os.getenv("XAI_API_KEY"):
        print("Error: XAI_API_KEY not set")
        sys.exit(1)

    # Prompt for confirmation
    confirm = input("\n⚠️  Start interactive project review with Grok? (yes/no): ").strip().lower()

    if confirm == "yes":
        run_interactive_review()
    else:
        print("Review cancelled.")