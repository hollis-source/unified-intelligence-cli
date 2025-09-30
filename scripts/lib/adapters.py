"""
Adapters for external services.

Following Dependency Inversion Principle:
- High-level modules depend on abstractions
- Abstractions are defined by interfaces (Protocol)
"""

import subprocess
import json
import sys
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path


class CommandExecutor(ABC):
    """Abstract command executor."""
    
    @abstractmethod
    def run(self, cmd: list[str], capture: bool = True) -> tuple[int, str, str]:
        """Execute command and return (returncode, stdout, stderr)."""
        pass


class SubprocessExecutor(CommandExecutor):
    """Concrete executor using subprocess."""
    
    def run(self, cmd: list[str], capture: bool = True) -> tuple[int, str, str]:
        """Execute command using subprocess."""
        if capture:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            return result.returncode, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd)
            return result.returncode, "", ""


class GitAdapter:
    """Adapter for Git operations."""
    
    def __init__(self, executor: CommandExecutor = None):
        self.executor = executor or SubprocessExecutor()
    
    def get_current_branch(self) -> str:
        """Get current Git branch."""
        code, stdout, stderr = self.executor.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
        if code != 0:
            raise RuntimeError(f"Failed to get branch: {stderr}")
        return stdout.strip()
    
    def get_remote_url(self) -> str:
        """Get remote URL."""
        code, stdout, stderr = self.executor.run(['git', 'remote', 'get-url', 'origin'])
        if code != 0:
            raise RuntimeError(f"Failed to get remote URL: {stderr}")
        return stdout.strip()
    
    def is_clean(self) -> bool:
        """Check if working directory is clean."""
        code, stdout, stderr = self.executor.run(['git', 'status', '--porcelain'])
        return code == 0 and not stdout.strip()
    
    def tag_exists(self, tag: str) -> bool:
        """Check if tag exists."""
        code, stdout, stderr = self.executor.run(['git', 'tag', '-l', tag])
        return code == 0 and bool(stdout.strip())
    
    def create_tag(self, tag: str, message: str) -> None:
        """Create annotated tag."""
        code, stdout, stderr = self.executor.run(['git', 'tag', '-a', tag, '-m', message])
        if code != 0:
            raise RuntimeError(f"Failed to create tag: {stderr}")
    
    def push_tag(self, tag: str) -> None:
        """Push tag to remote."""
        code, stdout, stderr = self.executor.run(['git', 'push', 'origin', tag])
        if code != 0:
            raise RuntimeError(f"Failed to push tag: {stderr}")
    
    def get_latest_tag(self) -> Optional[str]:
        """Get latest tag."""
        code, stdout, stderr = self.executor.run(['git', 'describe', '--tags', '--abbrev=0'])
        if code != 0:
            return None
        return stdout.strip()


class GitHubAdapter:
    """Adapter for GitHub CLI operations."""
    
    def __init__(self, executor: CommandExecutor = None):
        self.executor = executor or SubprocessExecutor()
    
    def is_authenticated(self) -> bool:
        """Check if gh CLI is authenticated."""
        code, stdout, stderr = self.executor.run(['gh', 'auth', 'status'])
        return code == 0
    
    def set_secret(self, name: str, value: str) -> None:
        """Set repository secret."""
        code, stdout, stderr = self.executor.run([
            'gh', 'secret', 'set', name,
            '--body', value
        ])
        if code != 0:
            raise RuntimeError(f"Failed to set secret {name}: {stderr}")
    
    def list_secrets(self) -> list[str]:
        """List repository secrets."""
        code, stdout, stderr = self.executor.run(['gh', 'secret', 'list', '--json', 'name'])
        if code != 0:
            raise RuntimeError(f"Failed to list secrets: {stderr}")
        
        try:
            secrets = json.loads(stdout)
            return [s['name'] for s in secrets]
        except json.JSONDecodeError:
            return []
    
    def get_workflow_runs(self, limit: int = 5) -> list[Dict[str, Any]]:
        """Get recent workflow runs."""
        code, stdout, stderr = self.executor.run([
            'gh', 'run', 'list',
            '--json', 'status,conclusion,name,createdAt,databaseId',
            '--limit', str(limit)
        ])
        if code != 0:
            raise RuntimeError(f"Failed to get workflow runs: {stderr}")
        
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return []
    
    def watch_workflow(self, run_id: str) -> None:
        """Watch workflow run (blocking)."""
        code, stdout, stderr = self.executor.run(
            ['gh', 'run', 'watch', run_id],
            capture=False
        )
        if code != 0:
            raise RuntimeError(f"Workflow failed: {stderr}")


class TestAdapter:
    """Adapter for running tests."""
    
    def __init__(self, executor: CommandExecutor = None):
        self.executor = executor or SubprocessExecutor()
    
    def run_tests(self) -> tuple[bool, str]:
        """Run pytest tests."""
        code, stdout, stderr = self.executor.run([
            sys.executable, '-m', 'pytest',
            'tests/', '-v'
        ])
        return code == 0, stdout + stderr
    
    def run_coverage(self, threshold: float = 85.0) -> tuple[bool, str]:
        """Run coverage check."""
        code, stdout, stderr = self.executor.run([
            sys.executable, '-m', 'pytest',
            'tests/',
            '--cov=src',
            '--cov-report=term',
            f'--cov-fail-under={threshold}'
        ])
        return code == 0, stdout + stderr
    
    def run_security_check(self) -> tuple[bool, str]:
        """Run bandit security scan."""
        code, stdout, stderr = self.executor.run([
            sys.executable, '-m', 'bandit',
            '-r', 'src/',
            '-ll'  # Only high severity
        ])
        return code == 0, stdout + stderr


class BuildAdapter:
    """Adapter for building packages."""
    
    def __init__(self, executor: CommandExecutor = None):
        self.executor = executor or SubprocessExecutor()
    
    def build_package(self) -> tuple[bool, str]:
        """Build Python package."""
        # Clean old builds
        code, stdout, stderr = self.executor.run([
            sys.executable, '-c',
            'import shutil; shutil.rmtree("dist", ignore_errors=True)'
        ])
        
        # Build
        code, stdout, stderr = self.executor.run([
            sys.executable, '-m', 'build'
        ])
        return code == 0, stdout + stderr
    
    def check_package(self) -> tuple[bool, str]:
        """Check package with twine."""
        code, stdout, stderr = self.executor.run([
            sys.executable, '-m', 'twine',
            'check', 'dist/*'
        ])
        return code == 0, stdout + stderr
