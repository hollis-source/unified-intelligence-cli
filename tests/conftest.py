"""
Pytest configuration for LLM cache tests.

Provides fixtures for Redis configuration and entity testing.
"""

import os
import pytest
from unittest.mock import MagicMock
from src.adapters.agent.llm_cache import CacheConfig
from src.entities.agent import Agent, Task


@pytest.fixture
def redis_config():
    """Provide Redis configuration for tests"""
    return CacheConfig(
        enabled=True,
        redis_host="localhost",
        redis_port=6379,
        redis_password=os.getenv("REDIS_PASSWORD", "cna_redis_2024"),
        ttl_seconds=86400
    )


@pytest.fixture
def short_ttl_config():
    """Provide Redis configuration with short TTL for testing expiration"""
    return CacheConfig(
        enabled=True,
        redis_host="localhost",
        redis_port=6379,
        redis_password=os.getenv("REDIS_PASSWORD", "cna_redis_2024"),
        ttl_seconds=1  # 1 second for testing
    )
