"""
User interface utilities for CLI.

Provides pretty printing, progress indicators, and user prompts.
"""

import sys
from typing import Optional
from .entities import Check, CheckStatus, Release, ReleaseStage


class Colors:
    """ANSI color codes."""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GRAY = '\033[90m'


def print_header(text: str) -> None:
    """Print section header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}\n")


def print_subheader(text: str) -> None:
    """Print subsection header."""
    print(f"\n{Colors.BOLD}{text}{Colors.RESET}")
    print(f"{Colors.GRAY}{'─' * 70}{Colors.RESET}")


def print_check(check: Check) -> None:
    """Print check result."""
    if check.status == CheckStatus.PASSED:
        icon = f"{Colors.GREEN}✓{Colors.RESET}"
        status = f"{Colors.GREEN}PASSED{Colors.RESET}"
    elif check.status == CheckStatus.FAILED:
        icon = f"{Colors.RED}✗{Colors.RESET}"
        status = f"{Colors.RED}FAILED{Colors.RESET}"
    elif check.status == CheckStatus.RUNNING:
        icon = f"{Colors.YELLOW}⋯{Colors.RESET}"
        status = f"{Colors.YELLOW}RUNNING{Colors.RESET}"
    elif check.status == CheckStatus.SKIPPED:
        icon = f"{Colors.GRAY}○{Colors.RESET}"
        status = f"{Colors.GRAY}SKIPPED{Colors.RESET}"
    else:
        icon = f"{Colors.GRAY}○{Colors.RESET}"
        status = f"{Colors.GRAY}PENDING{Colors.RESET}"
    
    required = "" if check.required else f"{Colors.GRAY}(optional){Colors.RESET}"
    print(f"  {icon} {check.description:40s} {status} {required}")
    
    if check.error_message and check.status == CheckStatus.FAILED:
        # Print first line of error
        error_lines = check.error_message.split('\n')
        print(f"     {Colors.RED}↳ {error_lines[0]}{Colors.RESET}")


def print_release_summary(release: Release) -> None:
    """Print release summary."""
    print_header("Release Summary")
    
    print(f"  Version:     {Colors.BOLD}{release.version}{Colors.RESET}")
    print(f"  Tag:         {Colors.BOLD}{release.tag_name}{Colors.RESET}")
    print(f"  Branch:      {release.branch}")
    print(f"  Stage:       {_format_stage(release.stage)}")
    
    passed = sum(1 for c in release.checks if c.passed)
    failed = sum(1 for c in release.checks if c.failed and c.required)
    total = len(release.checks)
    
    print(f"\n  Checks:      {Colors.GREEN}{passed} passed{Colors.RESET}, "
          f"{Colors.RED}{failed} failed{Colors.RESET}, {total} total")


def _format_stage(stage: ReleaseStage) -> str:
    """Format release stage with color."""
    colors = {
        ReleaseStage.PREFLIGHT: Colors.YELLOW,
        ReleaseStage.TAGGING: Colors.BLUE,
        ReleaseStage.PUBLISHING: Colors.CYAN,
        ReleaseStage.VERIFICATION: Colors.BLUE,
        ReleaseStage.COMPLETE: Colors.GREEN,
    }
    color = colors.get(stage, Colors.RESET)
    return f"{color}{stage.value.upper()}{Colors.RESET}"


def print_success(message: str) -> None:
    """Print success message."""
    print(f"\n{Colors.GREEN}✓ {message}{Colors.RESET}\n")


def print_error(message: str) -> None:
    """Print error message."""
    print(f"\n{Colors.RED}✗ {message}{Colors.RESET}\n", file=sys.stderr)


def print_warning(message: str) -> None:
    """Print warning message."""
    print(f"\n{Colors.YELLOW}⚠ {message}{Colors.RESET}\n")


def print_info(message: str) -> None:
    """Print info message."""
    print(f"{Colors.CYAN}ℹ {message}{Colors.RESET}")


def confirm(prompt: str, default: bool = False) -> bool:
    """
    Ask user for confirmation.
    
    Args:
        prompt: Question to ask
        default: Default answer if user just presses Enter
    
    Returns:
        True if user confirms, False otherwise
    """
    suffix = " [Y/n]" if default else " [y/N]"
    
    while True:
        response = input(f"{prompt}{suffix}: ").strip().lower()
        
        if not response:
            return default
        
        if response in ('y', 'yes'):
            return True
        elif response in ('n', 'no'):
            return False
        else:
            print("Please answer 'yes' or 'no'")


def prompt(message: str, default: Optional[str] = None, secret: bool = False) -> str:
    """
    Prompt user for input.
    
    Args:
        message: Prompt message
        default: Default value
        secret: Hide input (for passwords)
    
    Returns:
        User input
    """
    if default:
        message = f"{message} [{default}]"
    
    if secret:
        import getpass
        value = getpass.getpass(f"{message}: ")
    else:
        value = input(f"{message}: ").strip()
    
    return value if value else (default or "")


def print_progress(current: int, total: int, message: str = "") -> None:
    """
    Print progress bar.
    
    Args:
        current: Current progress
        total: Total items
        message: Optional message
    """
    if total == 0:
        return
    
    percent = int((current / total) * 100)
    bar_length = 40
    filled = int((current / total) * bar_length)
    bar = '█' * filled + '░' * (bar_length - filled)
    
    print(f"\r  [{bar}] {percent}% {message}", end='', flush=True)
    
    if current == total:
        print()  # New line when complete
