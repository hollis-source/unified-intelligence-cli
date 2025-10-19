"""
Pytest configuration for unit tests.

Configures anyio to only use asyncio backend (trio not installed).
"""

import pytest


@pytest.fixture(scope="session")
def anyio_backend():
    """Configure anyio to use only asyncio backend."""
    return "asyncio"
