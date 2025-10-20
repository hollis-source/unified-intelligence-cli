"""Workflow result caching - Performance optimization.

Caches workflow execution results to avoid redundant computations.
Supports TTL-based expiration and cache invalidation.

Clean Architecture: Use case layer (business logic)
SOLID: SRP (single responsibility - caching), DIP (depends on abstractions)
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime, timedelta


@dataclass
class CacheEntry:
    """Cached workflow result entry."""
    
    key: str
    result: Any
    timestamp: float
    ttl_seconds: Optional[int]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired.
        
        Returns:
            True if expired, False otherwise
        """
        if self.ttl_seconds is None:
            return False  # No expiration
        
        age = time.time() - self.timestamp
        return age > self.ttl_seconds
    
    def age_seconds(self) -> float:
        """Get age of cache entry in seconds."""
        return time.time() - self.timestamp


class WorkflowCache:
    """Workflow result cache with TTL support.
    
    Caches workflow execution results to avoid redundant computations.
    Supports:
    - TTL-based expiration
    - Cache invalidation
    - Hit/miss statistics
    - Memory-based storage (can be extended to Redis/disk)
    
    Example:
        >>> cache = WorkflowCache(default_ttl=3600)
        >>> cache.set("workflow1", result, ttl=1800)
        >>> cached = cache.get("workflow1")
        >>> if cached:
        ...     print("Cache hit!")
    """
    
    def __init__(
        self,
        default_ttl: Optional[int] = 3600,
        max_size: int = 1000,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize workflow cache.
        
        Args:
            default_ttl: Default TTL in seconds (None = no expiration)
            max_size: Maximum cache entries (LRU eviction)
            logger: Optional logger
        """
        self.default_ttl = default_ttl
        self.max_size = max_size
        self.logger = logger or logging.getLogger(__name__)
        
        self._cache: Dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached result.
        
        Args:
            key: Cache key
        
        Returns:
            Cached result or None if not found/expired
        """
        entry = self._cache.get(key)
        
        if entry is None:
            self._misses += 1
            self.logger.debug(f"Cache miss: {key}")
            return None
        
        if entry.is_expired():
            self.logger.debug(f"Cache expired: {key} (age: {entry.age_seconds():.1f}s)")
            del self._cache[key]
            self._misses += 1
            return None
        
        self._hits += 1
        self.logger.debug(f"Cache hit: {key} (age: {entry.age_seconds():.1f}s)")
        return entry.result
    
    def set(
        self,
        key: str,
        result: Any,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Set cached result.
        
        Args:
            key: Cache key
            result: Result to cache
            ttl: TTL in seconds (None = use default)
            metadata: Optional metadata
        """
        if ttl is None:
            ttl = self.default_ttl
        
        entry = CacheEntry(
            key=key,
            result=result,
            timestamp=time.time(),
            ttl_seconds=ttl,
            metadata=metadata or {}
        )
        
        self._cache[key] = entry
        self.logger.debug(f"Cache set: {key} (ttl: {ttl}s)")
        
        # Evict oldest if over max size
        if len(self._cache) > self.max_size:
            self._evict_oldest()
    
    def invalidate(self, key: str) -> bool:
        """Invalidate cache entry.
        
        Args:
            key: Cache key
        
        Returns:
            True if entry was removed, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            self.logger.debug(f"Cache invalidated: {key}")
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        self.logger.info(f"Cache cleared: {count} entries removed")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "total_requests": total_requests
        }
    
    def _evict_oldest(self) -> None:
        """Evict oldest cache entry (LRU)."""
        if not self._cache:
            return
        
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].timestamp)
        del self._cache[oldest_key]
        self.logger.debug(f"Cache evicted (LRU): {oldest_key}")
    
    @staticmethod
    def generate_key(workflow_file: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key from workflow file and parameters.
        
        Args:
            workflow_file: Workflow file path
            params: Optional parameters
        
        Returns:
            Cache key (hash)
        
        Example:
            >>> key = WorkflowCache.generate_key("workflow.ct", {"env": "prod"})
        """
        # Combine workflow file and params
        key_data = {
            "workflow": workflow_file,
            "params": params or {}
        }
        
        # Generate hash
        key_str = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_str.encode()).hexdigest()[:16]
        
        return f"workflow:{key_hash}"


class CachedWorkflowExecutor:
    """Workflow executor with result caching.
    
    Wraps any workflow executor to add caching capabilities.
    
    Example:
        >>> base_executor = LifecycleWorkflowExecutor()
        >>> cached_executor = CachedWorkflowExecutor(
        ...     base_executor,
        ...     cache=WorkflowCache(default_ttl=3600)
        ... )
        >>> result = await cached_executor.execute_workflow("workflow.ct")
    """
    
    def __init__(
        self,
        base_executor: Any,
        cache: Optional[WorkflowCache] = None,
        enable_cache: bool = True
    ):
        """Initialize cached executor.
        
        Args:
            base_executor: Base workflow executor
            cache: Workflow cache (creates default if None)
            enable_cache: Enable caching (default: True)
        """
        self.base_executor = base_executor
        self.cache = cache or WorkflowCache()
        self.enable_cache = enable_cache
    
    async def execute_workflow(
        self,
        workflow_file: str,
        verbose: bool = False,
        force_refresh: bool = False,
        **kwargs
    ) -> Any:
        """Execute workflow with caching.
        
        Args:
            workflow_file: Workflow file path
            verbose: Enable verbose output
            force_refresh: Force cache refresh
            **kwargs: Additional parameters
        
        Returns:
            Workflow execution result
        """
        # Generate cache key
        cache_key = WorkflowCache.generate_key(workflow_file, kwargs)
        
        # Check cache (if enabled and not forcing refresh)
        if self.enable_cache and not force_refresh:
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                if verbose:
                    print(f"✓ Cache hit: {workflow_file}")
                return cached_result
        
        # Execute workflow
        if verbose and self.enable_cache:
            print(f"✗ Cache miss: {workflow_file}")
        
        result = await self.base_executor.execute_workflow(
            workflow_file,
            verbose=verbose,
            **kwargs
        )
        
        # Cache result (if enabled and successful)
        if self.enable_cache and result.success:
            self.cache.set(cache_key, result)
        
        return result
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()
    
    def clear_cache(self) -> None:
        """Clear cache."""
        self.cache.clear()

