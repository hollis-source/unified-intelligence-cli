#!/usr/bin/env python3
"""
Verify release deployment.

Checks that the package was successfully deployed to:
- PyPI
- Docker Hub
- GitHub Releases

Usage:
    python scripts/verify-release.py --version 1.0.0
    python scripts/verify-release.py  # Auto-detect version
"""

import sys
import argparse
import subprocess
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.lib.ui import (
    print_header,
    print_subheader,
    print_success,
    print_error,
    print_warning,
    print_info,
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


def check_pypi(version: str) -> bool:
    """Check if package is available on PyPI."""
    print_subheader("Checking PyPI")
    
    try:
        result = subprocess.run(
            ['pip', 'index', 'versions', 'unified-intelligence-cli'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and version in result.stdout:
            print_success(f"Package version {version} found on PyPI")
            print_info(f"  URL: https://pypi.org/project/unified-intelligence-cli/{version}/")
            return True
        else:
            print_error(f"Package version {version} not found on PyPI")
            return False
    except Exception as e:
        print_error(f"Failed to check PyPI: {e}")
        return False


def check_docker(version: str, username: str = None) -> bool:
    """Check if Docker image is available."""
    print_subheader("Checking Docker Hub")
    
    if not username:
        print_warning("Docker username not provided, skipping Docker check")
        print_info("  Run with: --docker-username YOUR_USERNAME")
        return None
    
    image_name = f"{username}/unified-intelligence-cli:{version}"
    
    try:
        # Try to pull image metadata
        result = subprocess.run(
            ['docker', 'manifest', 'inspect', image_name],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print_success(f"Docker image {version} found")
            print_info(f"  Image: {image_name}")
            print_info(f"  URL: https://hub.docker.com/r/{username}/unified-intelligence-cli/tags")
            return True
        else:
            print_error(f"Docker image {version} not found")
            return False
    except Exception as e:
        print_error(f"Failed to check Docker: {e}")
        return False


def check_github_release(version: str) -> bool:
    """Check if GitHub release exists."""
    print_subheader("Checking GitHub Release")
    
    tag = f"v{version}"
    
    try:
        result = subprocess.run(
            ['gh', 'release', 'view', tag],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print_success(f"GitHub release {tag} found")
            
            # Extract URL from output
            for line in result.stdout.split('\n'):
                if 'url:' in line.lower():
                    print_info(f"  {line.strip()}")
            
            return True
        else:
            print_error(f"GitHub release {tag} not found")
            return False
    except Exception as e:
        print_error(f"Failed to check GitHub: {e}")
        return False


def test_installation(version: str) -> bool:
    """Test package installation in isolated environment."""
    print_subheader("Testing Installation")
    
    print_info("Creating temporary virtual environment...")
    
    try:
        # Create temp venv
        import tempfile
        import shutil
        
        with tempfile.TemporaryDirectory() as tmpdir:
            venv_path = Path(tmpdir) / "venv"
            
            # Create venv
            result = subprocess.run(
                [sys.executable, '-m', 'venv', str(venv_path)],
                capture_output=True,
                timeout=60
            )
            
            if result.returncode != 0:
                print_error("Failed to create virtual environment")
                return False
            
            # Determine pip path
            if sys.platform == 'win32':
                pip_path = venv_path / 'Scripts' / 'pip'
            else:
                pip_path = venv_path / 'bin' / 'pip'
            
            # Install package
            print_info(f"Installing unified-intelligence-cli=={version}...")
            
            result = subprocess.run(
                [str(pip_path), 'install', f'unified-intelligence-cli=={version}'],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                print_error(f"Installation failed: {result.stderr}")
                return False
            
            # Test import
            python_path = venv_path / 'bin' / 'python' if sys.platform != 'win32' else venv_path / 'Scripts' / 'python'
            
            result = subprocess.run(
                [str(python_path), '-c', 'import src.main; print("OK")'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and 'OK' in result.stdout:
                print_success("Package installs and imports successfully")
                return True
            else:
                print_error("Package import failed")
                return False
                
    except Exception as e:
        print_error(f"Installation test failed: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify release deployment"
    )
    parser.add_argument(
        '--version',
        help='Version to verify (default: read from pyproject.toml)'
    )
    parser.add_argument(
        '--docker-username',
        help='Docker Hub username'
    )
    parser.add_argument(
        '--skip-installation-test',
        action='store_true',
        help='Skip installation test'
    )
    
    args = parser.parse_args()
    
    # Read version
    try:
        version = args.version or read_version_from_pyproject()
    except Exception as e:
        print_error(f"Failed to read version: {e}")
        return 1
    
    # Print header
    print_header(f"Verifying Release: v{version}")
    print()
    
    # Run checks
    results = {}
    
    results['pypi'] = check_pypi(version)
    print()
    
    results['docker'] = check_docker(version, args.docker_username)
    print()
    
    results['github'] = check_github_release(version)
    print()
    
    # Test installation
    if not args.skip_installation_test:
        print_info("This will create a temporary virtual environment and test installation...")
        print_info("(May take 1-2 minutes)")
        print()
        results['installation'] = test_installation(version)
        print()
    
    # Summary
    print_header("Verification Summary")
    
    for name, status in results.items():
        if status is True:
            print(f"  {Colors.GREEN}✓{Colors.RESET} {name:20s} - OK")
        elif status is False:
            print(f"  {Colors.RED}✗{Colors.RESET} {name:20s} - Failed")
        else:
            print(f"  {Colors.GRAY}○{Colors.RESET} {name:20s} - Skipped")
    
    print()
    
    # Check if all passed
    failed = [name for name, status in results.items() if status is False]
    
    if not failed:
        print_success(f"Release {version} verified successfully!")
        return 0
    else:
        print_error(f"Verification failed for: {', '.join(failed)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
