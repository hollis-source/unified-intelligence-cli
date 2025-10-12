#!/usr/bin/env python3
"""
Interactive Grok Commit Review - Review recent commits for quality
Uses grok-code-fast-1 to review recent git commits and implementations.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.grok_session import GrokSession

# ============================================================================
# REVIEW TOOLS
# ============================================================================

def read_git_log(count: int = 10) -> str:
    """Read recent git commits with details."""
    try:
        result = subprocess.run(
            ['git', 'log', f'-{count}', '--format=%H|%an|%ar|%s', '--decorate'],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            formatted = []
            for line in lines:
                parts = line.split('|', 3)
                if len(parts) == 4:
                    commit_hash, author, date, message = parts
                    formatted.append(f"{commit_hash[:8]} | {author} | {date} | {message}")
            return "Recent commits:\n" + '\n'.join(formatted)
        else:
            return "Error reading git log"
    except Exception as e:
        return f"Error: {str(e)}"


def show_commit_diff(commit_hash: str) -> str:
    """Show diff for a specific commit."""
    try:
        result = subprocess.run(
            ['git', 'show', '--stat', commit_hash],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=15
        )

        if result.returncode == 0:
            # Limit output to avoid huge diffs
            output = result.stdout
            if len(output) > 5000:
                output = output[:5000] + "\n... (truncated, use read_file for full content)"
            return f"Commit {commit_hash[:8]}:\n{output}"
        else:
            return f"Error: Could not show commit {commit_hash}"
    except Exception as e:
        return f"Error: {str(e)}"


def show_commit_files(commit_hash: str) -> str:
    """List files changed in a commit."""
    try:
        result = subprocess.run(
            ['git', 'diff-tree', '--no-commit-id', '--name-status', '-r', commit_hash],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            return f"Files changed in {commit_hash[:8]}:\n{result.stdout}"
        else:
            return f"Error: Could not list files for {commit_hash}"
    except Exception as e:
        return f"Error: {str(e)}"


def show_file_diff(commit_hash: str, file_path: str) -> str:
    """Show diff for a specific file in a commit."""
    try:
        result = subprocess.run(
            ['git', 'show', f'{commit_hash}:{file_path}'],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            content = result.stdout
            if len(content) > 3000:
                content = content[:3000] + "\n... (truncated)"
            return f"File {file_path} at {commit_hash[:8]}:\n{content}"
        else:
            return f"Error: Could not show file {file_path} at {commit_hash}"
    except Exception as e:
        return f"Error: {str(e)}"


def read_file(file_path: str) -> str:
    """Read current contents of a file with line numbers."""
    try:
        full_path = project_root / file_path
        if not full_path.exists():
            return f"Error: File not found: {file_path}"

        content = full_path.read_text()
        lines = content.split('\n')

        # Add line numbers
        numbered = '\n'.join(f"{i+1:4d} | {line}" for i, line in enumerate(lines))
        return f"File: {file_path}\n{numbered}"
    except Exception as e:
        return f"Error reading {file_path}: {str(e)}"


def search_code(pattern: str, file_pattern: str = "*.py") -> str:
    """Search for pattern in code files."""
    try:
        result = subprocess.run(
            ['grep', '-r', '-n', '--include', file_pattern, pattern, str(project_root / 'src')],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[:20]
            return f"Found {len(lines)} matches:\n" + '\n'.join(lines)
        else:
            return f"No matches found for pattern: {pattern}"
    except Exception as e:
        return f"Error searching: {str(e)}"


def run_tests(test_path: str = "tests/") -> str:
    """Run tests and return results."""
    try:
        result = subprocess.run(
            ['pytest', test_path, '-v', '--tb=short'],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30
        )

        # Extract summary
        output_lines = result.stdout.split('\n')
        summary = [line for line in output_lines if 'passed' in line or 'failed' in line or 'error' in line]

        return f"Test results:\n" + '\n'.join(summary[-5:]) if summary else result.stdout[-1000:]
    except Exception as e:
        return f"Error running tests: {str(e)}"


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
        code_lines = sum(1 for line in lines if line.strip() and not line.strip().startswith('#'))

        return f"{file_path}: {total} total, {non_empty} non-empty, {code_lines} code lines"
    except Exception as e:
        return f"Error: {str(e)}"


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


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

REVIEW_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_git_log",
            "description": "Read recent git commits with hash, author, date, message",
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
            "name": "show_commit_diff",
            "description": "Show full diff (changes) for a specific commit",
            "parameters": {
                "type": "object",
                "properties": {
                    "commit_hash": {
                        "type": "string",
                        "description": "Git commit hash (full or short)"
                    }
                },
                "required": ["commit_hash"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "show_commit_files",
            "description": "List files changed in a specific commit",
            "parameters": {
                "type": "object",
                "properties": {
                    "commit_hash": {
                        "type": "string",
                        "description": "Git commit hash"
                    }
                },
                "required": ["commit_hash"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "show_file_diff",
            "description": "Show a specific file's content at a commit",
            "parameters": {
                "type": "object",
                "properties": {
                    "commit_hash": {
                        "type": "string",
                        "description": "Git commit hash"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to file"
                    }
                },
                "required": ["commit_hash", "file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read current contents of a file with line numbers",
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
            "name": "run_tests",
            "description": "Run tests and return summary",
            "parameters": {
                "type": "object",
                "properties": {
                    "test_path": {
                        "type": "string",
                        "description": "Path to tests (default: tests/)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "count_lines",
            "description": "Count total, non-empty, and code lines in a file",
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
    }
]


# ============================================================================
# MAIN
# ============================================================================

def run_commit_review():
    """Run interactive commit review with Grok."""

    print("=" * 80)
    print("GROK COMMIT REVIEW - INTERACTIVE CODE REVIEW")
    print("=" * 80)
    print()
    print("Using model: grok-code-fast-1")
    print("Tools available:")
    for tool in REVIEW_TOOLS:
        print(f"  ✓ {tool['function']['name']}")
    print()

    # Initialize session
    session = GrokSession(
        model="grok-code-fast-1",
        system_prompt="""You are Grok, an expert code reviewer specializing in Clean Architecture and SOLID principles.

Your task is to review recent git commits for code quality, architecture compliance, and potential issues.

**Review Focus:**
- Clean Architecture: Dependency rule, layer separation
- SOLID Principles: SRP, OCP, LSP, ISP, DIP
- Clean Code: Function size (<20 lines), meaningful names, no duplication
- Test quality: Coverage, meaningful assertions, edge cases
- Security: No secrets, proper error handling
- Performance: Async patterns, resource management

**Review Process:**
1. Read recent commits with read_git_log
2. For each recent commit:
   - Show commit diff to see changes
   - List files changed
   - Read modified files to understand implementation
   - Check tests were added/updated
   - Search for potential issues (TODOs, hardcoded values, etc.)
3. Analyze code quality against Clean Architecture/SOLID
4. Identify strengths and issues
5. Provide specific, actionable feedback

**Output Format:**
After thorough review, provide feedback in this format:

## COMMIT REVIEW SUMMARY

### Commit: [hash] - [message]

**Strengths:**
- [Specific positive observations with file:line references]

**Issues:**
- [Specific problems with severity and file:line references]

**Recommendations:**
- [Actionable improvements with examples]

### Overall Assessment:
- Architecture Compliance: [Score/10]
- Code Quality: [Score/10]
- Test Coverage: [Score/10]

Be specific, cite file names and line numbers, and provide evidence for your assessments."""
    )

    # Set up tools
    session.tools = REVIEW_TOOLS
    session.tool_functions = {
        "read_git_log": read_git_log,
        "show_commit_diff": show_commit_diff,
        "show_commit_files": show_commit_files,
        "show_file_diff": show_file_diff,
        "read_file": read_file,
        "search_code": search_code,
        "run_tests": run_tests,
        "count_lines": count_lines,
        "list_directory": list_directory
    }

    # Initial review prompt
    review_prompt = """Review the most recent commits (last 5-10) to the Unified Intelligence CLI project.

Focus on:
1. Architecture compliance (Clean Architecture, SOLID)
2. Code quality (Clean Code principles)
3. Test coverage
4. Security concerns
5. Performance patterns

Start by examining recent commits, then dive deep into the implementations."""

    print("Sending review task to Grok...")
    print("=" * 80)
    print()

    result = session.send_message(review_prompt)

    # Iterative review
    round_num = 1
    max_rounds = 25

    while result['tool_results'] and round_num < max_rounds:
        print(f"\nROUND {round_num}: Grok used {len(result['tool_results'])} tools")
        for i, tool_result in enumerate(result['tool_results'], 1):
            tool_name = tool_result.get('tool', 'unknown')
            args = tool_result.get('args', {})
            # Truncate long args
            args_str = str(args)
            if len(args_str) > 60:
                args_str = args_str[:60] + "..."
            print(f"  {i}. {tool_name}({args_str})")

        round_num += 1

        # Continue review
        if round_num < max_rounds - 2:
            follow_up = "Continue your review. Use more tools if needed to examine the commits thoroughly."
        else:
            follow_up = "Provide your final comprehensive COMMIT REVIEW SUMMARY with specific findings, scores, and recommendations."
        result = session.send_message(follow_up)

    # If we finished the loop without getting a summary, ask for one
    if not result.get('response') or len(result.get('response', '')) < 200:
        print("\nRequesting final summary...")
        result = session.send_message(
            "Please provide your complete COMMIT REVIEW SUMMARY now with all findings, scores, and recommendations."
        )

    # Final response
    print("\n" + "=" * 80)
    print("REVIEW COMPLETE")
    print("=" * 80)
    print()

    final_text = result.get('response', '')
    print(final_text)

    # Save to file
    output_file = project_root / "docs" / "grok_commit_review.md"
    output_file.write_text(f"""# Grok Commit Review

**Model:** grok-code-fast-1
**Date:** {os.popen('date').read().strip()}
**Rounds:** {round_num}

---

{final_text}
""")

    print("\n" + "=" * 80)
    print(f"Review saved to: {output_file.relative_to(project_root)}")
    print("=" * 80)


if __name__ == "__main__":
    # Check for API key
    if not os.getenv("XAI_API_KEY"):
        print("Error: XAI_API_KEY not set")
        sys.exit(1)

    # Prompt for confirmation
    confirm = input("\n⚠️  Start interactive commit review with Grok? (yes/no): ").strip().lower()

    if confirm == "yes":
        run_commit_review()
    else:
        print("Review cancelled.")