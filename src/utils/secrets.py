"""
Secrets Utility - Docker Secrets Support

Reads secrets from either:
1. Docker secrets files (mounted at /run/secrets/*)
2. Environment variables with *_FILE suffix pointing to secret files
3. Direct environment variables (fallback for development)

Security: Supports production Docker secrets pattern while maintaining dev compatibility.
Clean Architecture: Centralizes secret reading logic (SRP).
"""

import os
from pathlib import Path
from typing import Optional


def read_secret(secret_name: str) -> Optional[str]:
    """
    Read secret from Docker secret file or environment variable.

    Resolution order (prioritizes Docker secrets first for production):
    1. /run/secrets/<secret_name> → Docker secret mount (production)
    2. <SECRET_NAME>_FILE env var → read from file at that path
    3. <SECRET_NAME> env var → read directly (development fallback)
    4. Return None if not found

    Args:
        secret_name: Name of secret (e.g., "XAI_API_KEY", "REDIS_PASSWORD")

    Returns:
        Secret value (stripped of whitespace) or None if not found

    Examples:
        >>> # Production: /run/secrets/xai_api_key
        >>> read_secret("XAI_API_KEY")
        'xai-...'

        >>> # Development: XAI_API_KEY=xai-...
        >>> read_secret("XAI_API_KEY")
        'xai-...'
    """
    import logging
    logger = logging.getLogger(__name__)

    # Strategy 1: Check Docker secrets default location (production first)
    docker_secret_path = Path(f"/run/secrets/{secret_name.lower()}")
    if docker_secret_path.exists() and docker_secret_path.is_file():
        try:
            return docker_secret_path.read_text().strip()
        except (OSError, PermissionError) as e:
            logger.warning(f"Failed to read Docker secret {secret_name}: {e}")

    # Strategy 2: Check for *_FILE environment variable
    file_env_var = f"{secret_name}_FILE"
    file_path_str = os.getenv(file_env_var)

    if file_path_str:
        try:
            file_path = Path(file_path_str)
            if file_path.exists() and file_path.is_file():
                return file_path.read_text().strip()
        except (OSError, PermissionError) as e:
            logger.warning(f"Failed to read secret from {file_path_str}: {e}")

    # Strategy 3: Check direct environment variable (development fallback only)
    direct_value = os.getenv(secret_name)
    if direct_value:
        return direct_value.strip()

    # Not found
    return None


def require_secret(secret_name: str, error_message: Optional[str] = None) -> str:
    """
    Read secret and raise ValueError if not found.

    Args:
        secret_name: Name of secret
        error_message: Custom error message (optional)

    Returns:
        Secret value (never None)

    Raises:
        ValueError: If secret not found

    Examples:
        >>> require_secret("XAI_API_KEY", "XAI API key required. Get from: https://x.ai/api")
        'xai-...'
    """
    value = read_secret(secret_name)
    if value is None:
        if error_message:
            raise ValueError(error_message)
        else:
            raise ValueError(
                f"{secret_name} not found. Set {secret_name}_FILE or {secret_name} environment variable."
            )
    return value
