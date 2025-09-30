#!/usr/bin/env python3
"""
Setup GitHub repository secrets for release automation.

Interactively prompts for required secrets and sets them
using GitHub CLI (gh).

Required secrets:
- PYPI_API_TOKEN: PyPI API token for package publishing
- DOCKER_USERNAME: Docker Hub username
- DOCKER_PASSWORD: Docker Hub access token

Usage:
    python scripts/setup-secrets.py
    python scripts/setup-secrets.py --verify-only
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.lib.entities import Secret
from scripts.lib.adapters import GitHubAdapter
from scripts.lib.usecases import SetupSecrets
from scripts.lib.ui import (
    print_header,
    print_subheader,
    print_success,
    print_error,
    print_warning,
    print_info,
    prompt,
    confirm,
    Colors
)


REQUIRED_SECRETS = {
    'PYPI_API_TOKEN': Secret(
        name='PYPI_API_TOKEN',
        description='PyPI API token for package publishing',
        required=True
    ),
    'DOCKER_USERNAME': Secret(
        name='DOCKER_USERNAME',
        description='Docker Hub username',
        required=True
    ),
    'DOCKER_PASSWORD': Secret(
        name='DOCKER_PASSWORD',
        description='Docker Hub access token or password',
        required=True
    )
}


def print_instructions():
    """Print setup instructions."""
    print_header("GitHub Secrets Setup")
    
    print("This script will help you configure GitHub repository secrets")
    print("required for automated release to PyPI and Docker Hub.\n")
    
    print_subheader("Prerequisites")
    print("1. GitHub CLI (gh) installed and authenticated")
    print("   Install: https://cli.github.com/")
    print("   Auth: gh auth login\n")
    
    print("2. PyPI API token")
    print("   Create at: https://pypi.org/manage/account/token/")
    print("   Scope: 'Entire account' or specific to this project\n")
    
    print("3. Docker Hub credentials")
    print("   Username: Your Docker Hub username")
    print("   Token: Create at https://hub.docker.com/settings/security\n")


def verify_github_auth(github: GitHubAdapter) -> bool:
    """Verify GitHub CLI is authenticated."""
    print_info("Checking GitHub CLI authentication...")
    
    try:
        if github.is_authenticated():
            print_success("GitHub CLI is authenticated")
            return True
        else:
            print_error("GitHub CLI is not authenticated")
            print("\nPlease run: gh auth login")
            return False
    except Exception as e:
        print_error(f"Failed to check GitHub auth: {e}")
        return False


def verify_existing_secrets(use_case: SetupSecrets) -> dict[str, bool]:
    """Check which secrets are already set."""
    print_info("Checking existing secrets...")
    
    try:
        status = use_case.verify(list(REQUIRED_SECRETS.keys()))
        
        for name, is_set in status.items():
            secret = REQUIRED_SECRETS[name]
            if is_set:
                print(f"  {Colors.GREEN}✓{Colors.RESET} {name:20s} - Already set")
            else:
                print(f"  {Colors.RED}✗{Colors.RESET} {name:20s} - Not set")
        
        return status
    except Exception as e:
        print_error(f"Failed to verify secrets: {e}")
        return {}


def prompt_for_secrets(existing_status: dict[str, bool]) -> dict[str, str]:
    """Prompt user for secret values."""
    secrets = {}
    
    print_subheader("Enter Secret Values")
    print("(Press Enter to skip secrets that are already set)\n")
    
    for name, secret in REQUIRED_SECRETS.items():
        # Skip if already set
        if existing_status.get(name):
            skip = confirm(f"Secret {name} is already set. Update it?", default=False)
            if not skip:
                continue
        
        # Prompt for value
        print(f"\n{Colors.BOLD}{name}{Colors.RESET}")
        print(f"  {secret.description}")
        
        value = prompt("  Value", secret="PASSWORD" in name or "TOKEN" in name)
        
        if value:
            secrets[name] = value
        else:
            if secret.required and not existing_status.get(name):
                print_warning(f"  Skipping required secret {name}")
    
    return secrets


def set_secrets(use_case: SetupSecrets, secrets: dict[str, str]) -> bool:
    """Set secrets via GitHub CLI."""
    if not secrets:
        print_warning("No secrets to set")
        return True
    
    print_subheader("Setting Secrets")
    
    results = use_case.execute(secrets)
    
    all_success = True
    for name, success in results.items():
        if success:
            print(f"  {Colors.GREEN}✓{Colors.RESET} {name} - Set successfully")
        else:
            print(f"  {Colors.RED}✗{Colors.RESET} {name} - Failed to set")
            all_success = False
    
    return all_success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Setup GitHub repository secrets"
    )
    parser.add_argument(
        '--verify-only',
        action='store_true',
        help='Only verify existing secrets, do not set new ones'
    )
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Non-interactive mode (fail if secrets missing)'
    )
    
    args = parser.parse_args()
    
    # Print instructions
    if not args.non_interactive:
        print_instructions()
    
    # Initialize
    github = GitHubAdapter()
    use_case = SetupSecrets(github)
    
    # Verify GitHub auth
    if not verify_github_auth(github):
        return 1
    
    print()
    
    # Verify existing secrets
    existing_status = verify_existing_secrets(use_case)
    
    if not existing_status:
        print_error("Failed to check existing secrets")
        return 1
    
    # Check if all required secrets are set
    all_set = all(existing_status.get(name, False) for name in REQUIRED_SECRETS.keys())
    
    if args.verify_only:
        if all_set:
            print_success("All required secrets are configured!")
            return 0
        else:
            print_error("Some required secrets are missing")
            missing = [name for name, is_set in existing_status.items() if not is_set]
            print(f"\nMissing secrets: {', '.join(missing)}")
            return 1
    
    # Interactive mode
    if all_set and not args.non_interactive:
        print_success("\nAll required secrets are already configured!")
        
        if not confirm("Do you want to update any secrets?", default=False):
            return 0
    
    # Prompt for secrets
    if args.non_interactive:
        if not all_set:
            print_error("Some secrets are missing. Run in interactive mode to set them.")
            return 1
        return 0
    
    secrets_to_set = prompt_for_secrets(existing_status)
    
    # Set secrets
    if secrets_to_set:
        print()
        if set_secrets(use_case, secrets_to_set):
            print_success("\nSecrets configured successfully!")
            return 0
        else:
            print_error("\nFailed to set some secrets")
            return 1
    else:
        print_warning("\nNo secrets were updated")
        return 0


if __name__ == '__main__':
    sys.exit(main())
