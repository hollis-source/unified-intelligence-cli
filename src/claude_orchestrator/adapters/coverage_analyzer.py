"""CoverageAnalyzer Adapter.

Runs pytest with coverage and analyzes coverage gaps for task generation.

Clean Architecture: Adapter layer (implements ICoverageAnalyzer interface)
SOLID: LSP - substitutable for ICoverageAnalyzer
"""

import subprocess
import re
import json
from typing import List, Dict

from src.claude_orchestrator.interfaces.context_analyzer import (
    ICoverageAnalyzer,
    CoverageResults,
    CoverageAnalysisError,
)


class CoverageAnalyzer(ICoverageAnalyzer):
    """
    Pytest coverage analyzer.

    Runs pytest with coverage and parses results.

    Usage:
        analyzer = CoverageAnalyzer()
        results = analyzer.analyze_coverage("/path/to/project")
        print(f"Overall: {results.overall_percentage}%")
    """

    def __init__(self, timeout_seconds: int = 300):
        """
        Initialize coverage analyzer.

        Args:
            timeout_seconds: Timeout for coverage execution
        """
        self.timeout = timeout_seconds

    def analyze_coverage(
        self, project_path: str, min_coverage: float = 80.0
    ) -> CoverageResults:
        """
        Analyze code coverage.

        Args:
            project_path: Path to project root
            min_coverage: Minimum acceptable coverage percentage

        Returns:
            CoverageResults with coverage details
        """
        try:
            # Run pytest with coverage
            cmd = [
                "pytest",
                "--cov=src",
                "--cov-report=term-missing",
                "--quiet",
            ]

            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            # Parse coverage output
            return self._parse_coverage_output(result.stdout)

        except subprocess.TimeoutExpired:
            raise CoverageAnalysisError(
                f"Coverage analysis timed out after {self.timeout}s"
            )
        except Exception as e:
            raise CoverageAnalysisError(f"Coverage analysis failed: {e}")

    def get_uncovered_files(self, project_path: str) -> List[str]:
        """
        Get list of files with low coverage (<80%).

        Args:
            project_path: Path to project root

        Returns:
            List of file paths with <80% coverage
        """
        results = self.analyze_coverage(project_path)
        return [
            file_path
            for file_path, coverage in results.files_coverage.items()
            if coverage < 80.0
        ]

    def _parse_coverage_output(self, output: str) -> CoverageResults:
        """Parse coverage output to extract results."""
        files_coverage = {}
        uncovered_lines = {}
        total_lines = 0
        covered_lines = 0

        lines = output.split("\n")

        for line in lines:
            # Parse file coverage lines (e.g., "src/module.py    85%   10-15, 20")
            match = re.match(
                r"([\w/\.]+\.py)\s+(\d+)%(?:\s+([\d\-, ]+))?", line
            )
            if match:
                file_path = match.group(1)
                coverage_pct = float(match.group(2))
                missing_lines_str = match.group(3) or ""

                files_coverage[file_path] = coverage_pct

                # Parse missing lines
                if missing_lines_str:
                    missing_lines = self._parse_missing_lines(missing_lines_str)
                    uncovered_lines[file_path] = missing_lines

            # Parse TOTAL line
            if line.startswith("TOTAL"):
                match = re.search(r"(\d+)\s+(\d+)\s+(\d+)%", line)
                if match:
                    total_lines = int(match.group(1))
                    covered_lines = int(match.group(1)) - int(match.group(2))

        # Extract overall percentage
        overall_match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
        overall_percentage = (
            float(overall_match.group(1)) if overall_match else 0.0
        )

        return CoverageResults(
            overall_percentage=overall_percentage,
            files_coverage=files_coverage,
            uncovered_lines=uncovered_lines,
            total_lines=total_lines,
            covered_lines=covered_lines,
        )

    def _parse_missing_lines(self, missing_str: str) -> List[int]:
        """Parse missing lines string (e.g., '10-15, 20, 25-30')."""
        lines = []
        parts = missing_str.split(",")

        for part in parts:
            part = part.strip()
            if "-" in part:
                # Range (e.g., "10-15")
                start, end = part.split("-")
                lines.extend(range(int(start), int(end) + 1))
            elif part.isdigit():
                # Single line
                lines.append(int(part))

        return sorted(lines)
