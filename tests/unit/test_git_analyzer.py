import tempfile
import subprocess
from pathlib import Path

import pytest

from src.analysis.git_analyzer import GitAnalyzer, GitAnalysis


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True, capture_output=True)
        
        # Create some test files and commits
        test_file = repo_path / "test.py"
        test_file.write_text("# Test file\n")
        subprocess.run(["git", "add", "test.py"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feat: Add test file"], cwd=repo_path, check=True, capture_output=True)
        
        # Add more commits
        test_file.write_text("# Test file\n# Updated\n")
        subprocess.run(["git", "add", "test.py"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "fix: Fix bug in test file"], cwd=repo_path, check=True, capture_output=True)
        
        test_file.write_text("# Test file\n# Updated\n# Refactored\n")
        subprocess.run(["git", "add", "test.py"], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "refactor: Cleanup test file"], cwd=repo_path, check=True, capture_output=True)
        
        yield repo_path


def test_git_analyzer_initialization(temp_git_repo):
    """Test GitAnalyzer initialization."""
    analyzer = GitAnalyzer(repo_path=str(temp_git_repo))
    assert analyzer.repo_path == temp_git_repo


def test_git_analyzer_invalid_repo():
    """Test GitAnalyzer with invalid repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with pytest.raises(ValueError, match="Not a git repository"):
            GitAnalyzer(repo_path=tmpdir)


def test_analyze_commit_patterns(temp_git_repo):
    """Test commit pattern analysis."""
    analyzer = GitAnalyzer(repo_path=str(temp_git_repo))
    analysis = analyzer.analyze(days=30)
    
    assert isinstance(analysis, GitAnalysis)
    assert analysis.total_commits >= 3
    
    # Check for detected patterns
    assert 'feature' in analysis.commit_patterns or 'bug_fix' in analysis.commit_patterns or 'refactor' in analysis.commit_patterns


def test_high_churn_files(temp_git_repo):
    """Test high-churn file detection."""
    analyzer = GitAnalyzer(repo_path=str(temp_git_repo))
    
    # With threshold=1, test.py should be detected (3 commits)
    analysis = analyzer.analyze(days=30, high_churn_threshold=1)
    
    assert len(analysis.high_churn_files) > 0
    assert any('test.py' in f.file_path for f in analysis.high_churn_files)


def test_issue_themes_extraction(temp_git_repo):
    """Test issue theme extraction."""
    analyzer = GitAnalyzer(repo_path=str(temp_git_repo))
    analysis = analyzer.analyze(days=30)
    
    # Should extract some keywords from commit messages
    assert len(analysis.issue_themes) > 0
    
    # Themes should be tuples of (keyword, count)
    for theme, count in analysis.issue_themes:
        assert isinstance(theme, str)
        assert isinstance(count, int)
        assert count > 0

