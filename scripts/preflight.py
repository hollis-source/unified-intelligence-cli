#!/usr/bin/env python3
"""
Pre-flight checks for release.

Runs all automated checks before release:
- Git working directory clean
- Tests pass
- Coverage ≥ 85%
- No security issues
- Package builds successfully
- Package validation passes

Usage:
    python scripts/preflight.py
    python scripts/preflight.py --version 1.0.0
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.lib.entities import Release, CheckStatus
from scripts.lib.adapters import GitAdapter, TestAdapter, BuildAdapter, GitHubAdapter
from scripts.lib.usecases import RunPreflightChecks
from scripts.lib.ui import (
    print_header,
    print_subheader,
    print_check,
    print_release_summary,
    print_success,
    print_error,
    print_warning
)


def progress_callback(check, status):
    """Callback for check progress."""
    print_check(check)


def read_version_from_pyproject() -> str:
    """Read version from pyproject.toml."""
    import toml
    
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        raise FileNotFoundError("pyproject.toml not found")
    
    data = toml.load(pyproject_path)
    return data['project']['version']


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run pre-flight checks for release"
    )
    parser.add_argument(
        '--version',
        help='Version to release (default: read from pyproject.toml)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Read version
    try:
        version = args.version or read_version_from_pyproject()
    except Exception as e:
        print_error(f"Failed to read version: {e}")
        return 1
    
    # Create release object
    release = Release(
        version=version,
        tag_name=f"v{version}"
    )
    
    # Print header
    print_header(f"Pre-Flight Checks for Release {release.version}")
    
    # Initialize adapters
    git = GitAdapter()
    test = TestAdapter()
    build = BuildAdapter()
    github = GitHubAdapter()
    
    # Run checks
    use_case = RunPreflightChecks(git, test, build, github)
    
    print_subheader("Running Checks")
    
    try:
        release = use_case.execute(release, progress_callback=progress_callback)
    except Exception as e:
        print_error(f"Check execution failed: {e}")
        return 1
    
    # Print summary
    print_release_summary(release)
    
    # Check results
    if release.all_checks_passed:
        print_success(f"All checks passed! Ready to release {release.version}")
        return 0
    else:
        print_error("Some required checks failed. Please fix issues before releasing.")
        
        # Print failed checks
        print_subheader("Failed Checks")
        for check in release.failed_checks:
            print(f"\n{check.name}:")
            print(f"  {check.error_message}")
        
        return 1


if __name__ == '__main__':
    sys.exit(main())
