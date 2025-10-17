#!/usr/bin/env python3
"""
PostToolUse hook for automated git commits.

Triggers after Write/Edit/MultiEdit tools complete.
Analyzes git diff and uses Auggie MCP to generate commit messages.

Toggle: Set AUTOCOMMIT_DISABLE=1 to disable
Log: ~/.claude/autocommit.log

Author: Claude (Sonnet 4.5)
Date: 2025-10-11
"""

import os
import sys
import json
import subprocess
import time
import logging
from pathlib import Path
from datetime import datetime

# Configuration
AUTOCOMMIT_DISABLE = os.getenv("AUTOCOMMIT_DISABLE") == "1"
BATCH_WINDOW = int(os.getenv("AUTOCOMMIT_BATCH_WINDOW", "30"))  # seconds
TIMESTAMP_FILE = "/tmp/claude_autocommit_last_edit"
LOG_FILE = Path.home() / ".claude" / "autocommit.log"
MAX_DIFF_SIZE = int(os.getenv("AUTOCOMMIT_MAX_DIFF_SIZE", "10000"))  # characters
LOG_LEVEL = os.getenv("AUTOCOMMIT_LOG_LEVEL", "INFO")

# Setup logging
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s | %(levelname)-6s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def main():
    """Main hook entry point."""
    # Check if disabled
    if AUTOCOMMIT_DISABLE:
        logging.debug("Autocommit disabled via AUTOCOMMIT_DISABLE=1")
        sys.exit(0)

    try:
        # Read hook input from stdin
        hook_input = json.loads(sys.stdin.read())

        logging.debug(f"Hook input: {json.dumps(hook_input, indent=2)}")

        # Extract file paths from tool input
        file_paths = extract_file_paths(hook_input)

        if not file_paths:
            logging.debug("No files to commit")
            sys.exit(0)

        logging.info(f"Processing {len(file_paths)} file(s): {', '.join(file_paths)}")

        # Ensure repository is in a safe state before committing
        if not safe_to_commit():
            sys.exit(0)


        # Check if we should batch or commit now
        if should_batch():
            update_timestamp()
            logging.info(f"Batching {len(file_paths)} files (waiting for {BATCH_WINDOW}s window)")
            sys.exit(0)

        # Get git diff
        diff = get_git_diff(file_paths)

        if not diff or diff.strip() == "":
            logging.info("Empty diff, skipping commit")
            sys.exit(0)

        logging.debug(f"Diff size: {len(diff)} characters")

        # Generate commit message via Auggie
        commit_message = generate_commit_message(diff, file_paths)

        logging.debug(f"Generated message: {commit_message[:100]}...")

        # Stage files
        stage_files(file_paths)

        # Create commit
        commit_hash = create_commit(commit_message)

        # Log success
        log_commit(commit_hash, commit_message, len(file_paths))

        # Reset timestamp
        clear_timestamp()

    except Exception as e:
        logging.error(f"Hook error: {str(e)}", exc_info=True)
        # Don't fail - just log and continue
        sys.exit(0)


def extract_file_paths(hook_input: dict) -> list:
    """Extract file paths from hook input (robust to different payload shapes)."""
    file_paths: list[str] = []

    if not isinstance(hook_input, dict):
        return file_paths

    # Prefer nested tool_input, but fall back to top-level
    tool_input = hook_input.get('tool_input') or hook_input

    # Single-file keys commonly used by tools
    for key in ('file_path', 'path', 'new_file_path'):
        val = tool_input.get(key)
        if isinstance(val, str):
            file_paths.append(val)

    # MultiEdit-style payloads
    edits = tool_input.get('edits')
    if isinstance(edits, list):
        for edit in edits:
            if isinstance(edit, dict):
                for key in ('file_path', 'path', 'new_file_path'):
                    val = edit.get(key) if edit else None
                    if isinstance(val, str):
                        file_paths.append(val)

    return file_paths


def should_batch() -> bool:
    """Check if we should batch this edit or commit now."""
    if not os.path.exists(TIMESTAMP_FILE):
        return False

    try:
        last_edit = float(open(TIMESTAMP_FILE).read())
        elapsed = time.time() - last_edit
        return elapsed < BATCH_WINDOW
    except:
        return False


def update_timestamp():
    """Record current time as last edit."""
    with open(TIMESTAMP_FILE, 'w') as f:
        f.write(str(time.time()))


def clear_timestamp():
    """Clear timestamp file after commit."""
    if os.path.exists(TIMESTAMP_FILE):
        os.remove(TIMESTAMP_FILE)


def has_merge_conflicts() -> bool:
    """Return True if there are merge conflicts or a merge/rebase is in progress."""
    try:
        project_dir = os.getenv('CLAUDE_PROJECT_DIR', os.getcwd())
        # Check for conflict markers in status
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=project_dir
        )
        status = result.stdout.splitlines()
        if any(line.startswith(('UU', 'AA', 'DD')) for line in status):
            return True
        # Detect merge/rebase in progress
        git_dir_result = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=project_dir
        )
        git_dir = git_dir_result.stdout.strip() or '.git'
        merge_head = os.path.join(project_dir, git_dir, 'MERGE_HEAD')
        rebase_merge = os.path.join(project_dir, git_dir, 'rebase-merge')
        rebase_apply = os.path.join(project_dir, git_dir, 'rebase-apply')
        return any(os.path.exists(p) for p in (merge_head, rebase_merge, rebase_apply))
    except Exception:
        return False


def is_detached_head() -> bool:
    """Return True if HEAD is detached."""
    try:
        project_dir = os.getenv('CLAUDE_PROJECT_DIR', os.getcwd())
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=project_dir
        )
        return result.stdout.strip() == 'HEAD'
    except Exception:
        return False


def safe_to_commit() -> bool:
    """Check repository state to ensure it's safe to create a commit."""
    if is_detached_head():
        logging.warning('Skipping autocommit: detached HEAD')
        return False
    if has_merge_conflicts():
        logging.warning('Skipping autocommit: merge/rebase in progress or conflicts detected')
        return False
    return True



def get_git_diff(file_paths: list) -> str:
    """Get git diff for specified files."""
    try:
        project_dir = os.getenv('CLAUDE_PROJECT_DIR', os.getcwd())

        # Get diff for staged and unstaged changes
        result = subprocess.run(
            ['git', 'diff', 'HEAD'] + file_paths,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_dir
        )

        diff = result.stdout

        # Truncate if too large
        if len(diff) > MAX_DIFF_SIZE:
            logging.warning(f"Diff truncated from {len(diff)} to {MAX_DIFF_SIZE} characters")
            diff = diff[:MAX_DIFF_SIZE] + "\n\n... (diff truncated)"

        return diff

    except Exception as e:
        logging.error(f"Failed to get git diff: {str(e)}")
        return ""


def generate_commit_message(diff: str, file_paths: list) -> str:
    """Generate commit message using Auggie MCP."""
    try:
        # Get recent commits for style reference
        recent_commits = get_recent_commits(3)

        # Build prompt for Auggie
        prompt = build_commit_prompt(diff, file_paths, recent_commits)

        # Call Auggie MCP (try GPT-5 first, fallback to Claude)
        message = call_auggie_mcp(prompt)

        if message:
            logging.info("Commit message generated by Auggie")
            return message
        else:
            logging.warning("Auggie unavailable, using fallback message")
            return generate_fallback_message(file_paths)

    except Exception as e:
        logging.error(f"Failed to generate commit message: {str(e)}")
        return generate_fallback_message(file_paths)


def get_recent_commits(count: int = 3) -> list:
    """Get recent commit messages for style reference."""
    try:
        project_dir = os.getenv('CLAUDE_PROJECT_DIR', os.getcwd())

        result = subprocess.run(
            ['git', 'log', f'-{count}', '--format=%s%n%b%n---'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=project_dir
        )

        commits = result.stdout.split('---')
        return [c.strip() for c in commits if c.strip()][:count]

    except:
        return []


def build_commit_prompt(diff: str, file_paths: list, recent_commits: list) -> str:
    """Build prompt for Auggie to generate commit message."""
    prompt = f"""Analyze this git diff and generate a conventional commit message.

DIFF:
{diff}

FILES CHANGED:
{chr(10).join(f'- {fp}' for fp in file_paths)}

REQUIREMENTS:
- Use conventional commit format: <type>: <subject>
- Types: feat, fix, docs, refactor, test, chore, style, perf
- Subject: imperative mood, lowercase, no period, <50 chars
- Body: explain WHAT and WHY (not HOW), wrap at 72 chars
- Include benefits/impact if significant
- Match style of recent commits in this repo

RECENT COMMITS (for style reference):
{chr(10).join(recent_commits) if recent_commits else 'No recent commits'}

Generate ONLY the commit message, no explanation or markdown formatting.
Do NOT include Co-Authored-By footer (will be added automatically).
"""
    return prompt


def call_auggie_mcp(prompt: str) -> str:
    """
    Call Auggie MCP to generate commit message.

    NOTE: This is a placeholder implementation.
    In production, this should use the actual MCP protocol to call auggie_with_gpt5.

    For now, returns None to trigger fallback message generation.

    TODO: Implement actual MCP integration:
    1. Connect to Auggie MCP server
    2. Send prompt via MCP protocol
    3. Receive and parse response
    4. Extract commit message
    """
    try:
        # Placeholder: In real implementation, this would call Auggie MCP
        # For now, return None to use fallback

        # Example of what the real implementation might look like:
        # import socket
        # sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # sock.connect(('localhost', 3000))
        # request = {"method": "tools/call", "params": {"name": "auggie_with_gpt5", ...}}
        # sock.sendall(json.dumps(request).encode())
        # response = sock.recv(4096)
        # return parse_mcp_response(response)

        logging.debug("Auggie MCP integration not yet implemented, using fallback")
        return None

    except Exception as e:
        logging.error(f"Auggie MCP call failed: {str(e)}")
        return None


def generate_fallback_message(file_paths: list) -> str:
    """Generate simple fallback message when Auggie unavailable."""
    file_count = len(file_paths)

    # Determine type based on file extensions
    commit_type = "chore"
    if any(f.endswith('.md') or f.endswith('.txt') for f in file_paths):
        if all(f.endswith(('.md', '.txt', '.rst')) for f in file_paths):
            commit_type = "docs"
    elif any('test' in f.lower() for f in file_paths):
        commit_type = "test"

    if file_count == 1:
        filename = os.path.basename(file_paths[0])
        subject = f"{commit_type}: update {filename}"
    else:
        subject = f"{commit_type}: update {file_count} files"

    body = "Automatic commit (Auggie MCP unavailable)\n\nFiles modified:\n"
    body += "\n".join(f"- {os.path.basename(fp)}" for fp in file_paths[:5])

    if file_count > 5:
        body += f"\n... and {file_count - 5} more files"

    return f"{subject}\n\n{body}"


def stage_files(file_paths: list):
    """Stage files for commit."""
    try:
        project_dir = os.getenv('CLAUDE_PROJECT_DIR', os.getcwd())

        subprocess.run(
            ['git', 'add'] + file_paths,
            check=True,
            capture_output=True,
            timeout=10,
            cwd=project_dir
        )

        logging.debug(f"Staged {len(file_paths)} file(s)")

    except Exception as e:
        logging.error(f"Failed to stage files: {str(e)}")
        raise


def create_commit(message: str) -> str:
    """Create git commit and return commit hash."""
    try:
        project_dir = os.getenv('CLAUDE_PROJECT_DIR', os.getcwd())

        # Add co-author footer
        footer = "\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
        full_message = message + footer

        # Create commit
        subprocess.run(
            ['git', 'commit', '-m', full_message],
            check=True,
            capture_output=True,
            timeout=10,
            cwd=project_dir
        )

        # Get commit hash
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=project_dir
        )

        commit_hash = result.stdout.strip()[:7]
        logging.debug(f"Created commit: {commit_hash}")

        return commit_hash

    except Exception as e:
        logging.error(f"Failed to create commit: {str(e)}")
        raise


def log_commit(commit_hash: str, message: str, file_count: int):
    """Log successful commit."""
    subject = message.split('\n')[0]
    logging.info(f"{commit_hash} | {subject} | {file_count} files")


if __name__ == '__main__':
    main()

