"""
Tests for LLM Response Cache (SYD2 Fix)

Validates caching behavior for expensive ULTRATHINK tasks to reduce latency.
"""

import pytest
import time
from src.adapters.agent.llm_cache import LLMResponseCache, CacheConfig


class TestLLMResponseCache:
    """Test suite for LLM response caching"""

    def test_cache_initialization_with_redis_unavailable(self):
        """Test cache gracefully handles Redis being unavailable"""
        config = CacheConfig(
            enabled=True,
            redis_host="invalid-host-should-not-exist",
            redis_port=9999
        )
        cache = LLMResponseCache(config)

        # Should fall back to disabled state
        assert cache.enabled == False

    def test_cache_set_and_get(self, redis_config):
        """Test basic cache set and get operations"""
        cache = LLMResponseCache(redis_config)

        if not cache.enabled:
            pytest.skip("Redis not available")

        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "ULTRATHINK: Plan refactoring for router"}
        ]
        response = "Here is a detailed refactoring plan..."

        # Set cache
        result = cache.set(
            messages=messages,
            response=response,
            task_description="ultrathink:refactoring",
            model_name="grok"
        )
        assert result == True

        # Get from cache
        cached_response = cache.get(
            messages=messages,
            task_description="ultrathink:refactoring",
            model_name="grok"
        )
        assert cached_response == response

    def test_cache_miss(self, redis_config):
        """Test cache returns None on miss"""
        cache = LLMResponseCache(redis_config)

        if not cache.enabled:
            pytest.skip("Redis not available")

        messages = [
            {"role": "user", "content": "This message was never cached"}
        ]

        cached_response = cache.get(
            messages=messages,
            task_description="never_seen_before",
            model_name="grok"
        )
        assert cached_response is None

    def test_cache_ttl_expiration(self, short_ttl_config):
        """Test cache entries expire after TTL"""
        cache = LLMResponseCache(short_ttl_config)

        if not cache.enabled:
            pytest.skip("Redis not available")

        messages = [{"role": "user", "content": "test"}]
        response = "test response"

        cache.set(messages=messages, response=response, ttl=1)

        # Should exist immediately
        assert cache.get(messages=messages) == response

        # Wait for expiration
        time.sleep(2)

        # Should be expired
        assert cache.get(messages=messages) is None

    def test_cache_key_determinism(self):
        """Test that same inputs produce same cache key"""
        config = CacheConfig(enabled=True)
        cache = LLMResponseCache(config)

        messages1 = [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "ULTRATHINK: test"}
        ]
        messages2 = [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "ULTRATHINK: test"}
        ]

        key1 = cache._generate_cache_key(messages1, "ultrathink:test", "grok")
        key2 = cache._generate_cache_key(messages2, "ultrathink:test", "grok")

        assert key1 == key2

    def test_cache_key_uniqueness(self):
        """Test that different inputs produce different cache keys"""
        config = CacheConfig(enabled=True)
        cache = LLMResponseCache(config)

        messages1 = [{"role": "user", "content": "task 1"}]
        messages2 = [{"role": "user", "content": "task 2"}]

        key1 = cache._generate_cache_key(messages1)
        key2 = cache._generate_cache_key(messages2)

        assert key1 != key2

    def test_cache_invalidation(self, redis_config):
        """Test manual cache invalidation"""
        cache = LLMResponseCache(redis_config)

        if not cache.enabled:
            pytest.skip("Redis not available")

        messages = [{"role": "user", "content": "test"}]
        response = "test response"

        cache.set(messages=messages, response=response)
        assert cache.get(messages=messages) == response

        # Invalidate
        cache.invalidate(messages=messages)

        # Should be gone
        assert cache.get(messages=messages) is None

    def test_cache_stats(self, redis_config):
        """Test cache statistics retrieval"""
        cache = LLMResponseCache(redis_config)

        stats = cache.get_stats()

        assert "enabled" in stats

        if cache.enabled:
            assert stats["enabled"] == True
            assert "backend" in stats
            assert stats["backend"] == "redis"

    def test_cache_disabled_behavior(self):
        """Test that cache operations work gracefully when disabled"""
        config = CacheConfig(enabled=False)
        cache = LLMResponseCache(config)

        messages = [{"role": "user", "content": "test"}]

        # All operations should return False/None
        assert cache.set(messages=messages, response="test") == False
        assert cache.get(messages=messages) is None
        assert cache.invalidate(messages=messages) == False

        stats = cache.get_stats()
        assert stats["enabled"] == False
