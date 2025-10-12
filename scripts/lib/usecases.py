"""
Use cases for release automation.

Following Clean Architecture: use cases contain application-specific
business rules and orchestrate the flow of data.
"""

from typing import List, Callable, Optional
from .entities import Check, CheckStatus, Release, ReleaseStage
from .adapters import (
    GitAdapter,
    TestAdapter,
    BuildAdapter,
    GitHubAdapter
)


class RunPreflightChecks:
    """Use case: Run all pre-release checks."""
    
    def __init__(
        self,
        git: GitAdapter,
        test: TestAdapter,
        build: BuildAdapter,
        github: Optional[GitHubAdapter] = None
    ):
        self.git = git
        self.test = test
        self.build = build
        self.github = github
    
    def execute(self, release: Release, progress_callback: Callable = None) -> Release:
        """
        Execute all pre-flight checks.
        
        Args:
            release: Release object to check
            progress_callback: Optional callback for progress updates
        
        Returns:
            Updated release object
        """
        # Define checks
        checks = [
            Check("git_clean", "Working directory is clean", required=True),
            Check("tests_pass", "All tests pass", required=True),
            Check("coverage_ok", "Coverage ≥ 85%", required=True),
            Check("security_ok", "No security issues", required=True),
            Check("package_builds", "Package builds successfully", required=True),
            Check("package_valid", "Package passes validation", required=True),
            Check("github_auth", "GitHub CLI authenticated", required=False),
        ]
        
        release.checks = checks
        
        # Run checks
        for check in checks:
            if progress_callback:
                progress_callback(check, CheckStatus.RUNNING)
            
            try:
                if check.name == "git_clean":
                    if self.git.is_clean():
                        check.mark_passed()
                    else:
                        check.mark_failed("Working directory has uncommitted changes")
                
                elif check.name == "tests_pass":
                    passed, output = self.test.run_tests()
                    if passed:
                        check.mark_passed()
                    else:
                        check.mark_failed(f"Tests failed:\n{output[-500:]}")
                
                elif check.name == "coverage_ok":
                    passed, output = self.test.run_coverage(threshold=85.0)
                    if passed:
                        check.mark_passed()
                    else:
                        check.mark_failed(f"Coverage below 85%:\n{output[-500:]}")
                
                elif check.name == "security_ok":
                    passed, output = self.test.run_security_check()
                    if passed:
                        check.mark_passed()
                    else:
                        check.mark_failed(f"Security issues found:\n{output[-500:]}")
                
                elif check.name == "package_builds":
                    passed, output = self.build.build_package()
                    if passed:
                        check.mark_passed()
                    else:
                        check.mark_failed(f"Build failed:\n{output[-500:]}")
                
                elif check.name == "package_valid":
                    passed, output = self.build.check_package()
                    if passed:
                        check.mark_passed()
                    else:
                        check.mark_failed(f"Package validation failed:\n{output[-500:]}")
                
                elif check.name == "github_auth":
                    if self.github and self.github.is_authenticated():
                        check.mark_passed()
                    else:
                        check.mark_skipped("GitHub CLI not authenticated")
                
            except Exception as e:
                check.mark_failed(str(e))
            
            if progress_callback:
                progress_callback(check, check.status)
        
        return release


class CreateReleaseTag:
    """Use case: Create and push release tag."""
    
    def __init__(self, git: GitAdapter):
        self.git = git
    
    def execute(self, release: Release, force: bool = False) -> Release:
        """
        Create and push release tag.
        
        Args:
            release: Release object
            force: Force tag creation even if exists
        
        Returns:
            Updated release object
        """
        # Check if tag exists
        if self.git.tag_exists(release.tag_name):
            if not force:
                raise ValueError(f"Tag {release.tag_name} already exists")
            raise NotImplementedError("Force tag creation not implemented")
        
        # Create tag
        message = f"Release version {release.version}"
        self.git.create_tag(release.tag_name, message)
        
        # Push tag
        self.git.push_tag(release.tag_name)
        
        release.stage = ReleaseStage.PUBLISHING
        return release


class VerifyDeployment:
    """Use case: Verify package deployment."""
    
    def __init__(self, github: GitHubAdapter):
        self.github = github
    
    def execute(self, release: Release, wait: bool = True) -> Release:
        """
        Verify deployment by checking GitHub workflow.
        
        Args:
            release: Release object
            wait: Wait for workflow to complete
        
        Returns:
            Updated release object
        """
        # Get recent workflow runs
        runs = self.github.get_workflow_runs(limit=1)
        
        if not runs:
            raise RuntimeError("No workflow runs found")
        
        latest_run = runs[0]
        
        if wait and latest_run['status'] != 'completed':
            # Watch workflow
            self.github.watch_workflow(str(latest_run['databaseId']))
        
        # Check conclusion
        if latest_run['conclusion'] == 'success':
            release.stage = ReleaseStage.COMPLETE
        else:
            raise RuntimeError(f"Workflow failed: {latest_run['conclusion']}")
        
        return release


class SetupSecrets:
    """Use case: Setup GitHub repository secrets."""
    
    def __init__(self, github: GitHubAdapter):
        self.github = github
    
    def execute(self, secrets: dict[str, str]) -> dict[str, bool]:
        """
        Set multiple secrets.
        
        Args:
            secrets: Dict of secret name -> value
        
        Returns:
            Dict of secret name -> success status
        """
        results = {}
        
        for name, value in secrets.items():
            try:
                self.github.set_secret(name, value)
                results[name] = True
            except Exception as e:
                results[name] = False
        
        return results
    
    def verify(self, required_secrets: List[str]) -> dict[str, bool]:
        """
        Verify required secrets are set.
        
        Args:
            required_secrets: List of required secret names
        
        Returns:
            Dict of secret name -> is_set status
        """
        existing_secrets = self.github.list_secrets()
        
        return {
            name: name in existing_secrets
            for name in required_secrets
        }
