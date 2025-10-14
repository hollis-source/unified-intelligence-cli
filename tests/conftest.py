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


# Phase 1: Entity testing fixtures (Qwen3-generated)
@pytest.fixture
def mock_text_generator():
    """Mock ITextGenerator interface for testing."""
    return MagicMock()


@pytest.fixture
def sample_agent():
    """Sample Agent fixture for testing."""
    return Agent(
        role="coordinator",
        capabilities=["code_gen", "test"],
        tier=3,
        parent_agent="team_lead",
        specialization="python"
    )


@pytest.fixture
def sample_task():
    """Sample Task fixture for testing."""
    return Task(
        description="Implement login feature",
        priority=2,
        task_id="task_123",
        dependencies=["task_456"]
    )
