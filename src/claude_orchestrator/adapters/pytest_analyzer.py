"""PytestAnalyzer Adapter.

Runs pytest and analyzes test results for task generation context.

Clean Architecture: Adapter layer (implements ITestAnalyzer interface)
SOLID: LSP - substitutable for ITestAnalyzer
"""

import subprocess
import json
import re
from typing import List, Dict, Optional

from src.claude_orchestrator.interfaces.context_analyzer import (
    ITestAnalyzer,
    TestResults,
    TestAnalysisError,
)


class PytestAnalyzer(ITestAnalyzer):
    """
    Pytest test runner and analyzer.

    Runs pytest with JSON output and parses results.

    Usage:
        analyzer = PytestAnalyzer()
        results = analyzer.run_tests("/path/to/project")
        print(f"Pass rate: {results.pass_rate * 100}%")
    """

    def __init__(self, timeout_seconds: int = 300):
        """
        Initialize pytest analyzer.

        Args:
            timeout_seconds: Timeout for test execution
        """
        self.timeout = timeout_seconds

    def run_tests(
        self, project_path: str, test_path: Optional[str] = None
    ) -> TestResults:
        """
        Run tests and capture results.

        Args:
            project_path: Path to project root
            test_path: Optional specific test path

        Returns:
            TestResults with execution summary
        """
        try:
            # Build pytest command
            test_target = test_path or "tests/"
            cmd = [
                "pytest",
                test_target,
                "--tb=short",
                "-v",
                "--quiet",
            ]

            result = subprocess.run(
                cmd,
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )

            # Parse output
            return self._parse_pytest_output(result.stdout, result.stderr)

        except subprocess.TimeoutExpired:
            raise TestAnalysisError(
                f"Test execution timed out after {self.timeout}s"
            )
        except Exception as e:
            raise TestAnalysisError(f"Test execution failed: {e}")

    def get_failed_tests(self, project_path: str) -> List[Dict[str, str]]:
        """
        Get list of failed tests with details.

        Args:
            project_path: Path to project root

        Returns:
            List of failed test details
        """
        results = self.run_tests(project_path)
        return results.failures

    def _parse_pytest_output(self, stdout: str, stderr: str) -> TestResults:
        """Parse pytest output to extract results."""
        # Extract summary line (e.g., "5 passed, 2 failed in 1.23s")
        summary_pattern = r"(\d+) passed(?:, (\d+) failed)?(?:, (\d+) skipped)? in ([\d\.]+)s"
        match = re.search(summary_pattern, stdout)

        if match:
            passed = int(match.group(1))
            failed = int(match.group(2) or 0)
            skipped = int(match.group(3) or 0)
            time = float(match.group(4))
        else:
            # Fallback: count test results
            passed = stdout.count(" PASSED")
            failed = stdout.count(" FAILED")
            skipped = stdout.count(" SKIPPED")
            time = 0.0

        total = passed + failed + skipped
        pass_rate = passed / total if total > 0 else 0.0

        # Extract failures
        failures = self._extract_failures(stdout)

        return TestResults(
            total_tests=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            pass_rate=pass_rate,
            failures=failures,
            execution_time_seconds=time,
        )

    def _extract_failures(self, output: str) -> List[Dict[str, str]]:
        """Extract failed test details from output."""
        failures = []
        lines = output.split("\n")

        for i, line in enumerate(lines):
            if " FAILED " in line:
                # Extract test name
                test_match = re.search(r"(test_[\w]+)", line)
                test_name = test_match.group(1) if test_match else "unknown"

                # Look for error message in following lines
                error = ""
                for j in range(i + 1, min(i + 10, len(lines))):
                    if "Error" in lines[j] or "assert" in lines[j]:
                        error = lines[j].strip()
                        break

                failures.append({"test_name": test_name, "error_message": error})

        return failures
