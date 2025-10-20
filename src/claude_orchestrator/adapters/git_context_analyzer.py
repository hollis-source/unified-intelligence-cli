"""GitContextAnalyzer Adapter.

Analyzes git repository state to provide context for task generation.

Clean Architecture: Adapter layer (implements IGitAnalyzer interface)
SOLID: LSP - substitutable for IGitAnalyzer
"""

import subprocess
from typing import List, Dict
from datetime import datetime, timedelta
from pathlib import Path

from src.claude_orchestrator.interfaces.context_analyzer import (
    IGitAnalyzer,
    GitInfo,
    GitAnalysisError,
)


class GitContextAnalyzer(IGitAnalyzer):
    """
    Git repository analyzer using subprocess git commands.

    Analyzes:
    - Recent commit history
    - Modified files
    - Current branch
    - Uncommitted changes

    Usage:
        analyzer = GitContextAnalyzer()
        git_info = analyzer.analyze("/path/to/repo", commit_limit=10)
        print(f"Recent commits: {len(git_info.recent_commits)}")
        print(f"Modified files: {git_info.modified_files}")
    """

    def __init__(self, timeout_seconds: int = 30):
        """
        Initialize git analyzer.

        Args:
            timeout_seconds: Timeout for git commands
        """
        self.timeout = timeout_seconds

    def analyze(self, repo_path: str, commit_limit: int = 10) -> GitInfo:
        """
        Analyze git repository.

        Args:
            repo_path: Path to git repository
            commit_limit: Number of recent commits to analyze

        Returns:
            GitInfo with repository state

        Raises:
            GitAnalysisError: If analysis fails
        """
        if not self._is_git_repo(repo_path):
            raise GitAnalysisError(f"{repo_path} is not a git repository")

        try:
            recent_commits = self._get_recent_commits(repo_path, commit_limit)
            modified_files = self._get_modified_files(repo_path)
            current_branch = self._get_current_branch(repo_path)
            uncommitted = self._has_uncommitted_changes(repo_path)
            total = self._get_total_commits(repo_path)

            return GitInfo(
                recent_commits=recent_commits,
                modified_files=modified_files,
                current_branch=current_branch,
                uncommitted_changes=uncommitted,
                total_commits=total,
            )

        except Exception as e:
            raise GitAnalysisError(f"Git analysis failed: {e}")

    def get_modified_files_since(self, repo_path: str, since: datetime) -> List[str]:
        """
        Get files modified since a specific time.

        Args:
            repo_path: Path to git repository
            since: DateTime to check from

        Returns:
            List of modified file paths
        """
        try:
            # Git log with since date
            since_str = since.strftime("%Y-%m-%d %H:%M:%S")
            cmd = [
                "git",
                "-C",
                repo_path,
                "log",
                f"--since={since_str}",
                "--name-only",
                "--pretty=format:",
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout
            )

            if result.returncode != 0:
                raise GitAnalysisError(f"Git log failed: {result.stderr}")

            # Parse and deduplicate files
            files = [line.strip() for line in result.stdout.split("\n") if line.strip()]
            return list(set(files))

        except subprocess.TimeoutExpired:
            raise GitAnalysisError(f"Git command timed out after {self.timeout}s")
        except Exception as e:
            raise GitAnalysisError(f"Failed to get modified files: {e}")

    # Private helper methods

    def _is_git_repo(self, repo_path: str) -> bool:
        """Check if path is a git repository."""
        git_dir = Path(repo_path) / ".git"
        return git_dir.exists()

    def _get_recent_commits(self, repo_path: str, limit: int) -> List[Dict[str, str]]:
        """Get recent commits with metadata."""
        cmd = [
            "git",
            "-C",
            repo_path,
            "log",
            f"-{limit}",
            "--pretty=format:%H|%an|%ae|%ad|%s",
            "--date=iso",
        ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=self.timeout
        )

        if result.returncode != 0:
            raise GitAnalysisError(f"Git log failed: {result.stderr}")

        commits = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            parts = line.split("|")
            if len(parts) >= 5:
                commits.append({
                    "sha": parts[0][:8],  # Short SHA
                    "author": parts[1],
                    "email": parts[2],
                    "date": parts[3],
                    "message": parts[4],
                })

        return commits

    def _get_modified_files(self, repo_path: str) -> List[str]:
        """Get modified files in working directory (including untracked)."""
        # Get tracked modified files
        cmd = ["git", "-C", repo_path, "diff", "--name-only", "HEAD"]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=self.timeout
        )

        modified = [line.strip() for line in result.stdout.split("\n") if line.strip()]

        # Get untracked files
        cmd = ["git", "-C", repo_path, "ls-files", "--others", "--exclude-standard"]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=self.timeout
        )

        untracked = [line.strip() for line in result.stdout.split("\n") if line.strip()]

        return modified + untracked

    def _get_current_branch(self, repo_path: str) -> str:
        """Get current git branch."""
        cmd = ["git", "-C", repo_path, "branch", "--show-current"]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=self.timeout
        )

        if result.returncode != 0:
            raise GitAnalysisError(f"Failed to get branch: {result.stderr}")

        return result.stdout.strip() or "detached-HEAD"

    def _has_uncommitted_changes(self, repo_path: str) -> bool:
        """Check if there are uncommitted changes."""
        cmd = ["git", "-C", repo_path, "status", "--porcelain"]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=self.timeout
        )

        return bool(result.stdout.strip())

    def _get_total_commits(self, repo_path: str) -> int:
        """Get total number of commits in repository."""
        cmd = ["git", "-C", repo_path, "rev-list", "--count", "HEAD"]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=self.timeout
        )

        if result.returncode != 0:
            return 0

        try:
            return int(result.stdout.strip())
        except ValueError:
            return 0
