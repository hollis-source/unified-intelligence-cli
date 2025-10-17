"""Tests for workflow caching.

Tests cache functionality, TTL expiration, and statistics.
"""

import pytest
import time
from src.use_cases.workflow_cache import WorkflowCache, CacheEntry, CachedWorkflowExecutor


def test_cache_entry_not_expired():
    """Test cache entry not expired."""
    entry = CacheEntry(
        key="test",
        result="value",
        timestamp=time.time(),
        ttl_seconds=3600
    )
    
    assert entry.is_expired() is False


def test_cache_entry_expired():
    """Test cache entry expired."""
    entry = CacheEntry(
        key="test",
        result="value",
        timestamp=time.time() - 7200,  # 2 hours ago
        ttl_seconds=3600  # 1 hour TTL
    )
    
    assert entry.is_expired() is True


def test_cache_entry_no_expiration():
    """Test cache entry with no expiration."""
    entry = CacheEntry(
        key="test",
        result="value",
        timestamp=time.time() - 86400,  # 1 day ago
        ttl_seconds=None  # No expiration
    )
    
    assert entry.is_expired() is False


def test_cache_set_and_get():
    """Test setting and getting cache entries."""
    cache = WorkflowCache()
    
    cache.set("key1", "value1")
    result = cache.get("key1")
    
    assert result == "value1"


def test_cache_miss():
    """Test cache miss."""
    cache = WorkflowCache()
    
    result = cache.get("nonexistent")
    
    assert result is None


def test_cache_expiration():
    """Test cache expiration."""
    cache = WorkflowCache(default_ttl=1)  # 1 second TTL
    
    cache.set("key1", "value1")
    
    # Should be cached
    assert cache.get("key1") == "value1"
    
    # Wait for expiration
    time.sleep(1.1)
    
    # Should be expired
    assert cache.get("key1") is None


def test_cache_custom_ttl():
    """Test cache with custom TTL."""
    cache = WorkflowCache(default_ttl=3600)
    
    cache.set("key1", "value1", ttl=1)  # 1 second TTL
    
    # Should be cached
    assert cache.get("key1") == "value1"
    
    # Wait for expiration
    time.sleep(1.1)
    
    # Should be expired
    assert cache.get("key1") is None


def test_cache_invalidate():
    """Test cache invalidation."""
    cache = WorkflowCache()
    
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1"
    
    # Invalidate
    result = cache.invalidate("key1")
    assert result is True
    
    # Should be gone
    assert cache.get("key1") is None


def test_cache_invalidate_nonexistent():
    """Test invalidating nonexistent key."""
    cache = WorkflowCache()
    
    result = cache.invalidate("nonexistent")
    assert result is False


def test_cache_clear():
    """Test clearing cache."""
    cache = WorkflowCache()
    
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")
    
    assert len(cache._cache) == 3
    
    cache.clear()
    
    assert len(cache._cache) == 0


def test_cache_stats():
    """Test cache statistics."""
    cache = WorkflowCache()
    
    # Set some entries
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    
    # Generate hits and misses
    cache.get("key1")  # Hit
    cache.get("key1")  # Hit
    cache.get("key3")  # Miss
    
    stats = cache.get_stats()
    
    assert stats["size"] == 2
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert stats["total_requests"] == 3
    assert stats["hit_rate"] == pytest.approx(66.67, rel=0.1)


def test_cache_max_size_eviction():
    """Test cache eviction when max size exceeded."""
    cache = WorkflowCache(max_size=3)
    
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")
    
    assert len(cache._cache) == 3
    
    # Add one more (should evict oldest)
    cache.set("key4", "value4")
    
    assert len(cache._cache) == 3
    assert cache.get("key1") is None  # Oldest evicted
    assert cache.get("key4") == "value4"  # Newest present


def test_generate_cache_key():
    """Test cache key generation."""
    key1 = WorkflowCache.generate_key("workflow.ct")
    key2 = WorkflowCache.generate_key("workflow.ct")
    key3 = WorkflowCache.generate_key("workflow.ct", {"env": "prod"})
    
    # Same inputs = same key
    assert key1 == key2
    
    # Different params = different key
    assert key1 != key3


def test_generate_cache_key_param_order():
    """Test cache key generation with different param order."""
    key1 = WorkflowCache.generate_key("workflow.ct", {"a": 1, "b": 2})
    key2 = WorkflowCache.generate_key("workflow.ct", {"b": 2, "a": 1})
    
    # Same params, different order = same key
    assert key1 == key2


@pytest.mark.asyncio
async def test_cached_executor_cache_hit():
    """Test cached executor with cache hit."""
    # Mock base executor
    class MockExecutor:
        def __init__(self):
            self.call_count = 0
        
        async def execute_workflow(self, workflow_file, verbose=False, **kwargs):
            self.call_count += 1
            return type('Result', (), {'success': True, 'result': 'test'})()
    
    base_executor = MockExecutor()
    cached_executor = CachedWorkflowExecutor(base_executor)
    
    # First call (cache miss)
    result1 = await cached_executor.execute_workflow("workflow.ct")
    assert base_executor.call_count == 1
    
    # Second call (cache hit)
    result2 = await cached_executor.execute_workflow("workflow.ct")
    assert base_executor.call_count == 1  # Not called again
    
    assert result1.result == result2.result


@pytest.mark.asyncio
async def test_cached_executor_force_refresh():
    """Test cached executor with force refresh."""
    class MockExecutor:
        def __init__(self):
            self.call_count = 0
        
        async def execute_workflow(self, workflow_file, verbose=False, **kwargs):
            self.call_count += 1
            return type('Result', (), {'success': True, 'result': f'test{self.call_count}'})()
    
    base_executor = MockExecutor()
    cached_executor = CachedWorkflowExecutor(base_executor)
    
    # First call
    result1 = await cached_executor.execute_workflow("workflow.ct")
    assert base_executor.call_count == 1
    
    # Force refresh
    result2 = await cached_executor.execute_workflow("workflow.ct", force_refresh=True)
    assert base_executor.call_count == 2  # Called again
    
    assert result1.result != result2.result


@pytest.mark.asyncio
async def test_cached_executor_disabled():
    """Test cached executor with caching disabled."""
    class MockExecutor:
        def __init__(self):
            self.call_count = 0
        
        async def execute_workflow(self, workflow_file, verbose=False, **kwargs):
            self.call_count += 1
            return type('Result', (), {'success': True, 'result': 'test'})()
    
    base_executor = MockExecutor()
    cached_executor = CachedWorkflowExecutor(base_executor, enable_cache=False)
    
    # First call
    await cached_executor.execute_workflow("workflow.ct")
    assert base_executor.call_count == 1
    
    # Second call (should execute again, cache disabled)
    await cached_executor.execute_workflow("workflow.ct")
    assert base_executor.call_count == 2


@pytest.mark.asyncio
async def test_cached_executor_failed_execution():
    """Test cached executor doesn't cache failed executions."""
    class MockExecutor:
        def __init__(self):
            self.call_count = 0
        
        async def execute_workflow(self, workflow_file, verbose=False, **kwargs):
            self.call_count += 1
            return type('Result', (), {'success': False, 'result': None})()
    
    base_executor = MockExecutor()
    cached_executor = CachedWorkflowExecutor(base_executor)
    
    # First call (fails)
    await cached_executor.execute_workflow("workflow.ct")
    assert base_executor.call_count == 1
    
    # Second call (should execute again, failure not cached)
    await cached_executor.execute_workflow("workflow.ct")
    assert base_executor.call_count == 2


def test_cached_executor_get_stats():
    """Test getting cache statistics from cached executor."""
    base_executor = type('MockExecutor', (), {})()
    cached_executor = CachedWorkflowExecutor(base_executor)
    
    stats = cached_executor.get_cache_stats()
    
    assert "size" in stats
    assert "hits" in stats
    assert "misses" in stats


def test_cached_executor_clear_cache():
    """Test clearing cache from cached executor."""
    base_executor = type('MockExecutor', (), {})()
    cached_executor = CachedWorkflowExecutor(base_executor)
    
    # Add some entries
    cached_executor.cache.set("key1", "value1")
    cached_executor.cache.set("key2", "value2")
    
    assert len(cached_executor.cache._cache) == 2
    
    # Clear
    cached_executor.clear_cache()
    
    assert len(cached_executor.cache._cache) == 0

