"""
Git History Analyzer for ATADO

Analyzes git commit history to identify patterns, high-churn files, and improvement opportunities.
"""
from __future__ import annotations

import logging
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class CommitPattern:
    """Pattern identified in commit messages."""
    pattern_type: str  # bug_fix, feature, refactor, test, docs
    count: int
    examples: List[str] = field(default_factory=list)


@dataclass
class FileChurn:
    """Churn metrics for a file."""
    file_path: str
    commit_count: int
    line_changes: int
    last_modified: str


@dataclass
class GitAnalysis:
    """Results of git history analysis."""
    total_commits: int
    commit_patterns: Dict[str, CommitPattern]
    high_churn_files: List[FileChurn]
    issue_themes: List[Tuple[str, int]]  # (theme, count)
    analysis_period_days: int
    timestamp: str


class GitAnalyzer:
    """
    Analyzes git repository history to identify improvement opportunities.
    
    Features:
    - Identify commit patterns (bug fixes, features, refactors)
    - Detect high-churn files (frequently modified)
    - Extract common issues from commit messages
    - Suggest areas for improvement
    """
    
    # Commit message patterns
    PATTERNS = {
        'bug_fix': [r'\bfix\b', r'\bbug\b', r'\bhotfix\b', r'\bpatch\b'],
        'feature': [r'\bfeat\b', r'\bfeature\b', r'\badd\b', r'\bimplement\b'],
        'refactor': [r'\brefactor\b', r'\bcleanup\b', r'\brestructure\b'],
        'test': [r'\btest\b', r'\btesting\b', r'\bspec\b'],
        'docs': [r'\bdoc\b', r'\bdocs\b', r'\bdocumentation\b', r'\breadme\b'],
    }
    
    def __init__(self, repo_path: str = "."):
        """
        Initialize git analyzer.
        
        Args:
            repo_path: Path to git repository
        """
        self.repo_path = Path(repo_path)
        
        if not (self.repo_path / ".git").exists():
            raise ValueError(f"Not a git repository: {repo_path}")
    
    def analyze(self, days: int = 30, high_churn_threshold: int = 10) -> GitAnalysis:
        """
        Analyze git history for the specified period.
        
        Args:
            days: Number of days to analyze
            high_churn_threshold: Minimum commits to consider file high-churn
            
        Returns:
            GitAnalysis with patterns, high-churn files, and themes
        """
        since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # Get commit log
        commits = self._get_commits(since_date)
        
        # Analyze commit patterns
        patterns = self._analyze_commit_patterns(commits)
        
        # Identify high-churn files
        high_churn = self._identify_high_churn_files(since_date, high_churn_threshold)
        
        # Extract issue themes
        themes = self._extract_issue_themes(commits)
        
        return GitAnalysis(
            total_commits=len(commits),
            commit_patterns=patterns,
            high_churn_files=high_churn,
            issue_themes=themes,
            analysis_period_days=days,
            timestamp=datetime.now(UTC).isoformat()
        )
    
    def _get_commits(self, since_date: str) -> List[str]:
        """Get commit messages since date."""
        try:
            result = subprocess.run(
                ["git", "log", f"--since={since_date}", "--pretty=format:%s"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return [line.strip() for line in result.stdout.split('\n') if line.strip()]
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get git commits: {e}")
            return []
    
    def _analyze_commit_patterns(self, commits: List[str]) -> Dict[str, CommitPattern]:
        """Analyze commit messages for patterns."""
        pattern_counts = defaultdict(list)
        
        for commit in commits:
            commit_lower = commit.lower()
            for pattern_type, regexes in self.PATTERNS.items():
                for regex in regexes:
                    if re.search(regex, commit_lower):
                        pattern_counts[pattern_type].append(commit)
                        break  # Only count once per pattern type
        
        patterns = {}
        for pattern_type, matches in pattern_counts.items():
            patterns[pattern_type] = CommitPattern(
                pattern_type=pattern_type,
                count=len(matches),
                examples=matches[:3]  # Keep first 3 examples
            )
        
        return patterns
    
    def _identify_high_churn_files(self, since_date: str, threshold: int) -> List[FileChurn]:
        """Identify files with high commit frequency."""
        try:
            # Get file change stats
            result = subprocess.run(
                ["git", "log", f"--since={since_date}", "--name-only", "--pretty=format:"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Count file changes
            file_counts = Counter()
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    file_counts[line] += 1
            
            # Get detailed stats for high-churn files
            high_churn = []
            for file_path, count in file_counts.most_common():
                if count < threshold:
                    break
                
                # Get line changes
                line_changes = self._get_file_line_changes(file_path, since_date)
                
                # Get last modified date
                last_modified = self._get_last_modified(file_path)
                
                high_churn.append(FileChurn(
                    file_path=file_path,
                    commit_count=count,
                    line_changes=line_changes,
                    last_modified=last_modified
                ))
            
            return high_churn
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to identify high-churn files: {e}")
            return []
    
    def _get_file_line_changes(self, file_path: str, since_date: str) -> int:
        """Get total line changes for a file."""
        try:
            result = subprocess.run(
                ["git", "log", f"--since={since_date}", "--numstat", "--", file_path],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            total_changes = 0
            for line in result.stdout.split('\n'):
                parts = line.strip().split('\t')
                if len(parts) >= 2:
                    try:
                        added = int(parts[0]) if parts[0] != '-' else 0
                        deleted = int(parts[1]) if parts[1] != '-' else 0
                        total_changes += added + deleted
                    except ValueError:
                        pass
            
            return total_changes
            
        except subprocess.CalledProcessError:
            return 0
    
    def _get_last_modified(self, file_path: str) -> str:
        """Get last modified date for a file."""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ai", "--", file_path],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return "unknown"
    
    def _extract_issue_themes(self, commits: List[str], top_n: int = 10) -> List[Tuple[str, int]]:
        """Extract common themes from commit messages."""
        # Simple keyword extraction (in production, could use NLP)
        keywords = Counter()
        
        # Common stopwords to ignore
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can'
        }
        
        for commit in commits:
            # Extract words (lowercase, alphanumeric only)
            words = re.findall(r'\b[a-z]+\b', commit.lower())
            for word in words:
                if len(word) > 3 and word not in stopwords:
                    keywords[word] += 1
        
        return keywords.most_common(top_n)

