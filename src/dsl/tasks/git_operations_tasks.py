"""Git Operations Tasks - Real implementations for DSL workflow.

Clean Architecture: Use Cases layer (business logic for git operations).
SOLID: SRP - each task has one responsibility.

This module implements tasks for git operations: status, diff, add, commit, log.
"""

import asyncio
import subprocess
from typing import Any, Dict, List
from pathlib import Path


async def git_status(input_data: Any = None) -> Dict[str, Any]:
    """
    Get git status - show modified, untracked files.

    Returns:
        Git status information
    """
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )

    # Parse short status output
    lines = result.stdout.strip().split('\n') if result.stdout.strip() else []

    modified = []
    untracked = []
    staged = []

    for line in lines:
        if line.startswith('M '):
            modified.append(line[3:])
        elif line.startswith('??'):
            untracked.append(line[3:])
        elif line.startswith('A '):
            staged.append(line[3:])

    return {
        "task": "git_status",
        "status": "success",
        "modified_files": modified,
        "untracked_files": untracked,
        "staged_files": staged,
        "total_files": len(modified) + len(untracked),
        "output": result.stdout
    }


async def git_diff_stat(input_data: Any = None) -> Dict[str, Any]:
    """
    Get git diff statistics.

    Returns:
        Diff statistics (insertions, deletions, files changed)
    """
    result = subprocess.run(
        ["git", "diff", "--stat"],
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )

    return {
        "task": "git_diff_stat",
        "status": "success",
        "output": result.stdout,
        "has_changes": bool(result.stdout.strip())
    }


async def run_tests(input_data: Any = None) -> Dict[str, Any]:
    """
    Run pytest to verify code works before committing.

    Returns:
        Test results
    """
    result = subprocess.run(
        ["venv/bin/pytest", "tests/dsl/", "-q", "--tb=short"],
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )

    # Parse pytest output for pass/fail counts
    output = result.stdout + result.stderr
    passed = output.count(" passed")

    return {
        "task": "run_tests",
        "status": "success" if result.returncode == 0 else "failed",
        "exit_code": result.returncode,
        "tests_passed": result.returncode == 0,
        "output": output,
        "recommendation": "Proceed with commit" if result.returncode == 0 else "Fix failing tests before commit"
    }


async def stage_files(input_data: Any = None) -> Dict[str, Any]:
    """
    Stage files for commit (git add).

    Args:
        input_data: Optional dict with 'files' key (list of files to stage)
                   If not provided, uses input from previous task

    Returns:
        Staging results
    """
    files_to_stage = []

    # Get files from input_data
    if isinstance(input_data, dict):
        if 'files' in input_data:
            files_to_stage = input_data['files']
        elif 'modified_files' in input_data and 'untracked_files' in input_data:
            # From git_status output
            files_to_stage = input_data['modified_files'] + input_data['untracked_files']

    if not files_to_stage:
        # Default: stage everything
        files_to_stage = ["."]

    result = subprocess.run(
        ["git", "add"] + files_to_stage,
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )

    return {
        "task": "stage_files",
        "status": "success" if result.returncode == 0 else "failed",
        "files_staged": files_to_stage,
        "file_count": len(files_to_stage),
        "exit_code": result.returncode
    }


async def create_commit(input_data: Any = None) -> Dict[str, Any]:
    """
    Create git commit with generated message.

    Args:
        input_data: Optional dict with 'commit_message' key

    Returns:
        Commit results
    """
    # Generate commit message from input or use default
    commit_message = "WIP: Uncommitted changes\n\nAutomatic commit via DSL workflow"

    if isinstance(input_data, dict) and 'commit_message' in input_data:
        commit_message = input_data['commit_message']
    elif isinstance(input_data, dict) and 'modified_files' in input_data:
        # Generate message based on files
        file_count = input_data.get('total_files', 0)
        commit_message = f"Update: {file_count} files modified\n\nAutomatic commit via DSL workflow"

    # Add co-author footer
    commit_message += "\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>"

    result = subprocess.run(
        ["git", "commit", "-m", commit_message],
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )

    return {
        "task": "create_commit",
        "status": "success" if result.returncode == 0 else "failed",
        "exit_code": result.returncode,
        "commit_message": commit_message,
        "output": result.stdout,
        "error": result.stderr if result.returncode != 0 else None
    }


async def verify_commit(input_data: Any = None) -> Dict[str, Any]:
    """
    Verify commit was created successfully.

    Returns:
        Verification results with latest commit info
    """
    # Get latest commit hash
    result = subprocess.run(
        ["git", "log", "-1", "--oneline"],
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )

    return {
        "task": "verify_commit",
        "status": "success",
        "latest_commit": result.stdout.strip(),
        "commit_created": bool(result.stdout.strip())
    }


async def analyze_uncommitted_changes(input_data: Any = None) -> Dict[str, Any]:
    """
    Analyze uncommitted changes to categorize them.

    Returns:
        Analysis of uncommitted changes (docs, tests, src, etc.)
    """
    status_result = await git_status()

    modified = status_result.get('modified_files', [])
    untracked = status_result.get('untracked_files', [])
    all_files = modified + untracked

    # Categorize files
    docs = [f for f in all_files if f.startswith('docs/')]
    tests = [f for f in all_files if f.startswith('tests/')]
    src = [f for f in all_files if f.startswith('src/')]
    examples = [f for f in all_files if f.startswith('examples/')]
    scripts = [f for f in all_files if f.startswith('scripts/')]
    training = [f for f in all_files if f.startswith('training/')]
    config = [f for f in all_files if f.startswith('config/') or f.startswith('data/')]

    return {
        "task": "analyze_uncommitted_changes",
        "status": "success",
        "total_files": len(all_files),
        "categories": {
            "docs": {"count": len(docs), "files": docs},
            "tests": {"count": len(tests), "files": tests},
            "src": {"count": len(src), "files": src},
            "examples": {"count": len(examples), "files": examples},
            "scripts": {"count": len(scripts), "files": scripts},
            "training": {"count": len(training), "files": training},
            "config": {"count": len(config), "files": config}
        },
        "modified_files": modified,
        "untracked_files": untracked,
        "recommendation": "Review categories and commit related files together"
    }


async def generate_commit_message(input_data: Any = None) -> Dict[str, Any]:
    """
    Generate descriptive commit message based on changed files.

    Args:
        input_data: Analysis from analyze_uncommitted_changes

    Returns:
        Generated commit message
    """
    if not isinstance(input_data, dict) or 'categories' not in input_data:
        return {
            "task": "generate_commit_message",
            "status": "success",
            "commit_message": "Update: Multiple file changes\n\nAutomatic commit via DSL workflow"
        }

    categories = input_data['categories']
    total_files = input_data.get('total_files', 0)

    # Determine primary category
    primary_category = max(categories.items(), key=lambda x: x[1]['count'])
    category_name = primary_category[0]
    category_count = primary_category[1]['count']

    # Generate title
    title_map = {
        "docs": "Documentation",
        "tests": "Tests",
        "src": "Implementation",
        "examples": "Examples",
        "scripts": "Scripts",
        "training": "Training",
        "config": "Configuration"
    }

    title = f"{title_map.get(category_name, 'Update')}: "

    # Add description
    if category_count == total_files:
        title += f"{category_count} {category_name} files"
    else:
        title += f"{total_files} files ({category_count} {category_name})"

    # Build body
    body_lines = ["\nChanges include:"]
    for cat, data in categories.items():
        if data['count'] > 0:
            body_lines.append(f"- {data['count']} {cat} files")

    body = "\n".join(body_lines)

    message = f"{title}\n{body}\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>"

    return {
        "task": "generate_commit_message",
        "status": "success",
        "commit_message": message,
        "primary_category": category_name,
        "file_count": total_files
    }
