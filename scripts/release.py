#!/usr/bin/env python3
"""
Automated release orchestrator.

Orchestrates the entire release process:
1. Run pre-flight checks
2. Verify GitHub secrets configured
3. Create and push git tag
4. Monitor GitHub Actions workflow
5. Verify deployment

Usage:
    python scripts/release.py                  # Interactive mode
    python scripts/release.py --version 1.0.0  # Specify version
    python scripts/release.py --auto           # Fully automated (no prompts)
"""

import sys
import time
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.lib.entities import Release, ReleaseStage
from scripts.lib.adapters import (
    GitAdapter,
    TestAdapter,
    BuildAdapter,
    GitHubAdapter
)
from scripts.lib.usecases import (
    RunPreflightChecks,
    CreateReleaseTag,
    SetupSecrets,
    VerifyDeployment
)
from scripts.lib.ui import (
    print_header,
    print_subheader,
    print_check,
    print_release_summary,
    print_success,
    print_error,
    print_warning,
    print_info,
    confirm,
    Colors
)


def read_version_from_pyproject() -> str:
    """Read version from pyproject.toml."""
    import toml
    
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        raise FileNotFoundError("pyproject.toml not found")
    
    data = toml.load(pyproject_path)
    return data['project']['version']


def check_progress(check, status):
    """Callback for check progress."""
    print_check(check)


def run_preflight_checks(
    release: Release,
    git: GitAdapter,
    test: TestAdapter,
    build: BuildAdapter,
    github: GitHubAdapter
) -> bool:
    """Run pre-flight checks."""
    print_header("Step 1: Pre-Flight Checks")
    
    use_case = RunPreflightChecks(git, test, build, github)
    
    try:
        release = use_case.execute(release, progress_callback=check_progress)
    except Exception as e:
        print_error(f"Check execution failed: {e}")
        return False
    
    print()
    
    if release.all_checks_passed:
        print_success("All pre-flight checks passed!")
        return True
    else:
        print_error("Some required checks failed")
        
        # Print failed checks
        for check in release.failed_checks:
            print(f"\n{Colors.RED}Failed:{Colors.RESET} {check.name}")
            print(f"  {check.error_message[:200]}")
        
        return False


def verify_secrets(github: GitHubAdapter) -> bool:
    """Verify GitHub secrets are configured."""
    print_header("Step 2: Verify GitHub Secrets")
    
    use_case = SetupSecrets(github)
    required_secrets = ['PYPI_API_TOKEN', 'DOCKER_USERNAME', 'DOCKER_PASSWORD']
    
    try:
        status = use_case.verify(required_secrets)
    except Exception as e:
        print_error(f"Failed to verify secrets: {e}")
        return False
    
    all_set = all(status.values())
    
    for name, is_set in status.items():
        if is_set:
            print(f"  {Colors.GREEN}✓{Colors.RESET} {name}")
        else:
            print(f"  {Colors.RED}✗{Colors.RESET} {name} - Not set")
    
    print()
    
    if all_set:
        print_success("All required secrets are configured!")
        return True
    else:
        print_error("Some secrets are missing")
        print("\nRun: python scripts/setup-secrets.py")
        return False


def create_and_push_tag(release: Release, git: GitAdapter) -> bool:
    """Create and push release tag."""
    print_header("Step 3: Create and Push Release Tag")
    
    print_info(f"Creating tag: {release.tag_name}")
    print_info(f"Version: {release.version}")
    
    use_case = CreateReleaseTag(git)
    
    try:
        release = use_case.execute(release)
        print_success(f"Tag {release.tag_name} created and pushed!")
        return True
    except Exception as e:
        print_error(f"Failed to create/push tag: {e}")
        return False


def monitor_workflow(release: Release, github: GitHubAdapter) -> bool:
    """Monitor GitHub Actions workflow."""
    print_header("Step 4: Monitor GitHub Actions Workflow")
    
    print_info("Waiting for workflow to start...")
    time.sleep(5)  # Give GitHub time to process tag
    
    try:
        runs = github.get_workflow_runs(limit=1)
        
        if not runs:
            print_warning("No workflow runs found yet")
            print_info("Check manually: gh run list")
            return True  # Don't fail, user can check manually
        
        latest_run = runs[0]
        run_id = str(latest_run['databaseId'])
        
        print_info(f"Workflow run ID: {run_id}")
        print_info(f"Status: {latest_run['status']}")
        print()
        
        # Watch workflow
        print_info("Watching workflow (this may take several minutes)...")
        print()
        
        use_case = VerifyDeployment(github)
        release = use_case.execute(release, wait=True)
        
        print()
        print_success("Workflow completed successfully!")
        return True
        
    except Exception as e:
        print_error(f"Workflow failed: {e}")
        return False


def verify_deployment(release: Release) -> bool:
    """Verify deployment on PyPI and Docker Hub."""
    print_header("Step 5: Verify Deployment")
    
    print_info("Please verify the release manually:")
    print()
    
    print(f"  {Colors.BOLD}PyPI:{Colors.RESET}")
    print(f"    https://pypi.org/project/unified-intelligence-cli/{release.version}/")
    print()
    
    print(f"  {Colors.BOLD}Docker Hub:{Colors.RESET}")
    print(f"    https://hub.docker.com/r/YOUR_USERNAME/unified-intelligence-cli/tags")
    print()
    
    print(f"  {Colors.BOLD}GitHub Release:{Colors.RESET}")
    print(f"    https://github.com/YOUR_USERNAME/unified-intelligence-cli/releases/tag/{release.tag_name}")
    print()
    
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated release orchestrator"
    )
    parser.add_argument(
        '--version',
        help='Version to release (default: read from pyproject.toml)'
    )
    parser.add_argument(
        '--auto',
        action='store_true',
        help='Fully automated mode (no prompts)'
    )
    parser.add_argument(
        '--skip-preflight',
        action='store_true',
        help='Skip pre-flight checks (not recommended)'
    )
    parser.add_argument(
        '--skip-secrets-check',
        action='store_true',
        help='Skip secrets verification (not recommended)'
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
    
    # Initialize adapters
    git = GitAdapter()
    test = TestAdapter()
    build = BuildAdapter()
    github = GitHubAdapter()
    
    # Print release info
    print_header(f"Automated Release: v{version}")
    print()
    print(f"  Version:     {Colors.BOLD}{release.version}{Colors.RESET}")
    print(f"  Tag:         {Colors.BOLD}{release.tag_name}{Colors.RESET}")
    print(f"  Branch:      {git.get_current_branch()}")
    print()
    
    # Confirm if not auto mode
    if not args.auto:
        if not confirm(f"Proceed with release {release.version}?", default=True):
            print_info("Release cancelled")
            return 0
    
    # Step 1: Pre-flight checks
    if not args.skip_preflight:
        if not run_preflight_checks(release, git, test, build, github):
            if not args.auto:
                if not confirm("Pre-flight checks failed. Continue anyway?", default=False):
                    return 1
            else:
                return 1
    else:
        print_warning("Skipping pre-flight checks")
    
    # Step 2: Verify secrets
    if not args.skip_secrets_check:
        if not verify_secrets(github):
            return 1
    else:
        print_warning("Skipping secrets verification")
    
    # Confirm before tagging
    if not args.auto:
        print()
        if not confirm(f"Ready to create tag {release.tag_name} and trigger release?", default=True):
            print_info("Release cancelled")
            return 0
    
    # Step 3: Create and push tag
    if not create_and_push_tag(release, git):
        return 1
    
    # Step 4: Monitor workflow
    if not monitor_workflow(release, github):
        print_warning("Workflow monitoring failed, but tag was pushed")
        print_info("Check workflow status: gh run list")
    
    # Step 5: Verify deployment
    verify_deployment(release)
    
    # Success!
    print_header("Release Complete!")
    print()
    print(f"  {Colors.GREEN}✓{Colors.RESET} Version {Colors.BOLD}{release.version}{Colors.RESET} released successfully!")
    print()
    print_info("Next steps:")
    print("  1. Verify package on PyPI and Docker Hub (links above)")
    print("  2. Test installation: pip install unified-intelligence-cli")
    print("  3. Announce the release")
    print("  4. Begin alpha rollout (Week 3-4)")
    print()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
