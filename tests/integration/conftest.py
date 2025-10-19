"""
Pytest configuration for integration tests.
Configures anyio to only use asyncio backend (trio not needed for integration tests).
"""
import pytest

@pytest.fixture(scope="session")
def anyio_backend():
    """Configure anyio to use only asyncio backend."""
    return "asyncio"
