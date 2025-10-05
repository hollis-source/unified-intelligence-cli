"""
LLM Response Caching Layer - Performance optimization for expensive ULTRATHINK tasks.

Implements semantic caching with Redis backend to reduce latency for repeated queries.
Addresses SYD2 anomaly detection: architecture/refactoring tasks with 80s latency.

Architecture:
- Strategy pattern: Cache hit/miss strategies
- Dependency Injection: Redis client injected
- Single Responsibility: Only caches LLM responses

Performance Impact:
- Cache hit: <100ms (vs 80s for Grok API)
- Expected hit rate: ~30% for architecture analysis tasks
- TTL: 4 hours (reduced from 24h - codebase changes invalidate plans)
"""

import hashlib
import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """Configuration for LLM caching"""
    enabled: bool = True
    ttl_seconds: int = 14400  # 4 hours (reduced from 24h - codebase changes invalidate plans)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    key_prefix: str = "llm_cache:"


class LLMResponseCache:
    """
    Semantic cache for LLM responses.

    Cache Strategy:
    - Key: Hash of (task_description, messages, model_config)
    - Value: JSON-serialized LLM response
    - Backend: Redis (fallback to no-op if unavailable)
    - Invalidation: TTL-based (24h default)

    Thread-safe: Redis operations are atomic
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialize cache with configuration.

        Args:
            config: Cache configuration (uses defaults if None)
        """
        self.config = config or CacheConfig()
        self.client: Optional[Any] = None
        self.enabled = self.config.enabled and REDIS_AVAILABLE

        if self.enabled:
            try:
                self.client = redis.Redis(
                    host=self.config.redis_host,
                    port=self.config.redis_port,
                    db=self.config.redis_db,
                    password=self.config.redis_password,
                    decode_responses=True,
                    socket_connect_timeout=2,  # Fast fail if Redis unavailable
                    socket_timeout=2
                )
                # Test connection
                self.client.ping()
                logger.info(
                    f"LLM cache initialized: {self.config.redis_host}:{self.config.redis_port}"
                )
            except Exception as e:
                logger.warning(f"Redis unavailable, caching disabled: {e}")
                self.enabled = False
                self.client = None
        else:
            reason = "Redis not installed" if not REDIS_AVAILABLE else "Cache disabled in config"
            logger.info(f"LLM caching disabled: {reason}")

    def _generate_cache_key(
        self,
        messages: List[Dict[str, Any]],
        task_description: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> str:
        """
        Generate deterministic cache key from request parameters.

        Args:
            messages: Conversation messages
            task_description: Optional task description for better keying
            model_name: Model name to include in key

        Returns:
            Cache key string
        """
        # Build cache key components
        key_data = {
            "messages": messages,
            "task": task_description or "",
            "model": model_name or "default"
        }

        # Generate stable hash
        key_json = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_json.encode()).hexdigest()[:16]

        return f"{self.config.key_prefix}{key_hash}"

    def get(
        self,
        messages: List[Dict[str, Any]],
        task_description: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Retrieve cached response if available.

        Args:
            messages: Conversation messages
            task_description: Optional task description
            model_name: Model name

        Returns:
            Cached response or None if cache miss
        """
        if not self.enabled or not self.client:
            return None

        try:
            cache_key = self._generate_cache_key(messages, task_description, model_name)
            cached_value = self.client.get(cache_key)

            if cached_value:
                logger.info(f"Cache HIT for key: {cache_key[:32]}...")
                return cached_value
            else:
                logger.debug(f"Cache MISS for key: {cache_key[:32]}...")
                return None

        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None

    def set(
        self,
        messages: List[Dict[str, Any]],
        response: str,
        task_description: Optional[str] = None,
        model_name: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store response in cache.

        Args:
            messages: Conversation messages
            response: LLM response to cache
            task_description: Optional task description
            model_name: Model name
            ttl: Time-to-live in seconds (uses default if None)

        Returns:
            True if successfully cached, False otherwise
        """
        if not self.enabled or not self.client:
            return False

        try:
            cache_key = self._generate_cache_key(messages, task_description, model_name)
            ttl_seconds = ttl or self.config.ttl_seconds

            self.client.setex(
                name=cache_key,
                time=ttl_seconds,
                value=response
            )

            logger.info(f"Cache SET for key: {cache_key[:32]}... (TTL: {ttl_seconds}s)")
            return True

        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False

    def invalidate(
        self,
        messages: List[Dict[str, Any]],
        task_description: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> bool:
        """
        Manually invalidate cache entry.

        Args:
            messages: Conversation messages
            task_description: Optional task description
            model_name: Model name

        Returns:
            True if invalidated, False otherwise
        """
        if not self.enabled or not self.client:
            return False

        try:
            cache_key = self._generate_cache_key(messages, task_description, model_name)
            result = self.client.delete(cache_key)
            logger.info(f"Cache INVALIDATE for key: {cache_key[:32]}...")
            return bool(result)
        except Exception as e:
            logger.warning(f"Cache invalidate error: {e}")
            return False

    def clear_all(self) -> bool:
        """
        Clear all cached responses (use with caution).

        Returns:
            True if cleared, False otherwise
        """
        if not self.enabled or not self.client:
            return False

        try:
            pattern = f"{self.config.key_prefix}*"
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
                logger.warning(f"Cache CLEAR ALL: {len(keys)} keys deleted")
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        if not self.enabled or not self.client:
            return {"enabled": False}

        try:
            info = self.client.info("stats")
            pattern = f"{self.config.key_prefix}*"
            key_count = len(self.client.keys(pattern))

            return {
                "enabled": True,
                "backend": "redis",
                "host": f"{self.config.redis_host}:{self.config.redis_port}",
                "cached_responses": key_count,
                "ttl_seconds": self.config.ttl_seconds,
                "total_commands": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"enabled": True, "error": str(e)}
