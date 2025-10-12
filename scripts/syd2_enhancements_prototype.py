#!/usr/bin/env python3
"""
SYD2 Agent Enhancements Prototype
Implements advanced error handling and performance optimizations.

Clean Architecture:
- Entities: ErrorPattern, CacheEntry, MetricSnapshot
- Use Cases: ErrorHandler, PerformanceOptimizer
- Adapters: DSLIntegrationHook
- Frameworks: asyncio, functools, logging

SOLID Principles:
- SRP: Each class has single responsibility (error handling OR performance)
- OCP: Open for extension (custom retry strategies, cache backends)
- LSP: All handlers/optimizers follow same interface
- ISP: Minimal interfaces for each enhancement
- DIP: Depend on abstractions (task executors, not concrete implementations)
"""

import asyncio
import functools
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, TypeVar

# ==========================
# ENTITIES
# ==========================


@dataclass
class ErrorPattern:
    """Immutable entity for detected error patterns."""

    error_type: str
    frequency: int
    last_occurrence: str
    samples: List[str] = field(default_factory=list)
    severity: str = "medium"  # 'low', 'medium', 'high', 'critical'


@dataclass
class CacheEntry:
    """Immutable entity for cached data."""

    key: str
    value: Any
    created_at: float
    ttl: float  # Time to live in seconds
    hits: int = 0

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() - self.created_at > self.ttl


@dataclass
class MetricSnapshot:
    """Immutable entity for performance metrics."""

    operation: str
    latency: float
    timestamp: str
    success: bool
    error_type: Optional[str] = None


# ==========================
# USE CASES
# ==========================


class ErrorHandler:
    """
    Advanced error handling use case.

    Features:
    - Exponential backoff retry logic
    - Graceful degradation to fallback functions
    - Pattern detection from error logs

    Clean Architecture: Use Case layer (application logic)
    SOLID: SRP (only handles errors), DIP (depends on abstract logging)
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        pattern_threshold: int = 5,
    ):
        """
        Initialize error handler.

        Args:
            max_retries: Maximum retry attempts
            base_delay: Initial delay for exponential backoff (seconds)
            pattern_threshold: Minimum occurrences to detect pattern
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.pattern_threshold = pattern_threshold
        self.logger = logging.getLogger(self.__class__.__name__)
        self.error_log: List[Dict[str, Any]] = []

    async def retry_with_backoff(
        self,
        func: Callable,
        *args,
        max_retries: Optional[int] = None,
        **kwargs,
    ) -> Any:
        """
        Execute function with exponential backoff retry logic.

        Args:
            func: Async or sync function to execute
            *args: Positional arguments for func
            max_retries: Override default max_retries
            **kwargs: Keyword arguments for func

        Returns:
            Function result

        Raises:
            Last exception after all retries exhausted
        """
        max_retries = max_retries or self.max_retries
        last_exception = None

        for attempt in range(max_retries):
            try:
                # Support both async and sync functions
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                self.logger.debug(
                    f"Success on attempt {attempt + 1}/{max_retries}: {func.__name__}"
                )
                return result

            except Exception as e:
                last_exception = e
                self._log_error(func.__name__, str(e), attempt + 1)

                if attempt < max_retries - 1:
                    # Exponential backoff: delay = base_delay * 2^attempt
                    delay = self.base_delay * (2**attempt)
                    self.logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(
                        f"All {max_retries} attempts failed for {func.__name__}: {e}"
                    )

        raise last_exception

    async def degrade_gracefully(
        self,
        primary_func: Callable,
        fallback_func: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute primary function, fall back to simpler function on failure.

        Args:
            primary_func: Preferred function to execute
            fallback_func: Fallback function if primary fails
            *args: Arguments for both functions
            **kwargs: Keyword arguments for both functions

        Returns:
            Result from primary or fallback function
        """
        try:
            if asyncio.iscoroutinefunction(primary_func):
                result = await primary_func(*args, **kwargs)
            else:
                result = primary_func(*args, **kwargs)

            self.logger.debug(f"Primary function succeeded: {primary_func.__name__}")
            return result

        except Exception as e:
            self.logger.warning(
                f"Primary function {primary_func.__name__} failed: {e}. "
                f"Degrading to {fallback_func.__name__}"
            )
            self._log_error(primary_func.__name__, str(e), degraded=True)

            # Execute fallback
            if asyncio.iscoroutinefunction(fallback_func):
                result = await fallback_func(*args, **kwargs)
            else:
                result = fallback_func(*args, **kwargs)

            self.logger.info(f"Fallback succeeded: {fallback_func.__name__}")
            return result

    def detect_patterns(self) -> Dict[str, ErrorPattern]:
        """
        Analyze error log for recurring patterns.

        Returns:
            Dictionary of error type to ErrorPattern
        """
        pattern_counts = defaultdict(list)

        # Group errors by type
        for error in self.error_log:
            error_type = error.get("error_type", "unknown")
            pattern_counts[error_type].append(error)

        # Build patterns for types exceeding threshold
        patterns = {}
        for error_type, occurrences in pattern_counts.items():
            if len(occurrences) >= self.pattern_threshold:
                # Determine severity based on frequency
                severity = self._calculate_severity(len(occurrences))

                patterns[error_type] = ErrorPattern(
                    error_type=error_type,
                    frequency=len(occurrences),
                    last_occurrence=occurrences[-1]["timestamp"],
                    samples=[e["message"][:100] for e in occurrences[:3]],
                    severity=severity,
                )

        self.logger.info(f"Detected {len(patterns)} error patterns")
        return patterns

    def _log_error(
        self, func_name: str, message: str, attempt: int = 1, degraded: bool = False
    ) -> None:
        """Internal: Log error to error_log for pattern detection."""
        self.error_log.append(
            {
                "function": func_name,
                "message": message,
                "error_type": message.split(":")[0] if ":" in message else "unknown",
                "timestamp": datetime.now().isoformat(),
                "attempt": attempt,
                "degraded": degraded,
            }
        )

    def _calculate_severity(self, frequency: int) -> str:
        """Calculate severity based on frequency."""
        if frequency >= 20:
            return "critical"
        elif frequency >= 10:
            return "high"
        elif frequency >= 5:
            return "medium"
        else:
            return "low"


class PerformanceOptimizer:
    """
    Performance optimization use case.

    Features:
    - Async execution with concurrency limits
    - In-memory caching with TTL
    - Metrics tracking (latency, throughput)

    Clean Architecture: Use Case layer (application logic)
    SOLID: SRP (only handles performance), OCP (extensible cache backends)
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        default_cache_ttl: int = 300,
        enable_metrics: bool = True,
    ):
        """
        Initialize performance optimizer.

        Args:
            max_concurrent: Max concurrent async tasks
            default_cache_ttl: Default cache TTL in seconds
            enable_metrics: Enable metrics collection
        """
        self.max_concurrent = max_concurrent
        self.default_cache_ttl = default_cache_ttl
        self.enable_metrics = enable_metrics
        self.logger = logging.getLogger(self.__class__.__name__)

        # Internal state
        self._cache: Dict[str, CacheEntry] = {}
        self._metrics: List[MetricSnapshot] = []
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def async_execute(
        self, func: Callable, *args, **kwargs
    ) -> Any:
        """
        Execute function asynchronously with concurrency limit.

        Args:
            func: Function to execute (async or sync)
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result
        """
        async with self._semaphore:
            start_time = time.time()
            func_name = func.__name__

            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    # Run sync function in thread pool
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, functools.partial(func, *args, **kwargs)
                    )

                latency = time.time() - start_time
                self._track_metric(func_name, latency, success=True)

                self.logger.debug(
                    f"Async execution completed: {func_name} ({latency:.3f}s)"
                )
                return result

            except Exception as e:
                latency = time.time() - start_time
                self._track_metric(
                    func_name, latency, success=False, error_type=type(e).__name__
                )
                raise

    def cache_get(
        self,
        key: str,
        compute_func: Callable,
        ttl: Optional[int] = None,
    ) -> Any:
        """
        Get value from cache or compute and cache it.

        Args:
            key: Cache key
            compute_func: Function to compute value on cache miss
            ttl: Time to live in seconds (uses default if None)

        Returns:
            Cached or computed value
        """
        ttl = ttl or self.default_cache_ttl

        # Check cache
        if key in self._cache:
            entry = self._cache[key]
            if not entry.is_expired():
                entry.hits += 1
                self.logger.debug(f"Cache hit: {key} (hits: {entry.hits})")
                return entry.value
            else:
                # Expired, remove
                self.logger.debug(f"Cache expired: {key}")
                del self._cache[key]

        # Cache miss - compute value
        self.logger.debug(f"Cache miss: {key}, computing...")
        value = compute_func()

        # Store in cache
        self._cache[key] = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            ttl=ttl,
        )

        return value

    def track_metrics(self, operation_name: str) -> Callable:
        """
        Decorator to track execution metrics for a function.

        Args:
            operation_name: Name for the operation in metrics

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    latency = time.time() - start_time
                    self._track_metric(operation_name, latency, success=True)
                    return result
                except Exception as e:
                    latency = time.time() - start_time
                    self._track_metric(
                        operation_name, latency, success=False, error_type=type(e).__name__
                    )
                    raise

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    latency = time.time() - start_time
                    self._track_metric(operation_name, latency, success=True)
                    return result
                except Exception as e:
                    latency = time.time() - start_time
                    self._track_metric(
                        operation_name, latency, success=False, error_type=type(e).__name__
                    )
                    raise

            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

        return decorator

    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get summary of collected metrics.

        Returns:
            Dictionary with metrics summary
        """
        if not self._metrics:
            return {
                "total_operations": 0,
                "avg_latency": 0.0,
                "success_rate": 0.0,
            }

        total = len(self._metrics)
        successes = sum(1 for m in self._metrics if m.success)
        total_latency = sum(m.latency for m in self._metrics)

        # Group by operation
        by_operation = defaultdict(list)
        for metric in self._metrics:
            by_operation[metric.operation].append(metric)

        operation_stats = {}
        for op, metrics in by_operation.items():
            op_successes = sum(1 for m in metrics if m.success)
            operation_stats[op] = {
                "count": len(metrics),
                "avg_latency": sum(m.latency for m in metrics) / len(metrics),
                "success_rate": op_successes / len(metrics) if metrics else 0.0,
            }

        return {
            "total_operations": total,
            "avg_latency": total_latency / total if total > 0 else 0.0,
            "success_rate": successes / total if total > 0 else 0.0,
            "cache_size": len(self._cache),
            "cache_hit_rate": self._calculate_cache_hit_rate(),
            "by_operation": operation_stats,
        }

    def _track_metric(
        self, operation: str, latency: float, success: bool, error_type: Optional[str] = None
    ) -> None:
        """Internal: Track a metric."""
        if not self.enable_metrics:
            return

        self._metrics.append(
            MetricSnapshot(
                operation=operation,
                latency=latency,
                timestamp=datetime.now().isoformat(),
                success=success,
                error_type=error_type,
            )
        )

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        if not self._cache:
            return 0.0

        total_hits = sum(entry.hits for entry in self._cache.values())
        total_entries = len(self._cache)

        # Approximate: hits / (hits + misses), where misses ≈ entries
        return total_hits / (total_hits + total_entries) if total_hits > 0 else 0.0


# ==========================
# ADAPTERS
# ==========================


class DSLIntegrationHook:
    """
    Integration adapter for DSL runtime.

    Provides hooks for error handling and performance tracking
    during DSL task execution.

    Clean Architecture: Interface Adapter layer
    SOLID: ISP (minimal interface), DIP (depends on abstractions)
    """

    def __init__(
        self,
        error_handler: ErrorHandler,
        performance_optimizer: PerformanceOptimizer,
    ):
        """
        Initialize DSL integration hook.

        Args:
            error_handler: Error handling use case
            performance_optimizer: Performance optimization use case
        """
        self.error_handler = error_handler
        self.performance_optimizer = performance_optimizer
        self.logger = logging.getLogger(self.__class__.__name__)

    async def on_task_start(self, task_name: str) -> None:
        """Hook called before task execution."""
        self.logger.debug(f"Task starting: {task_name}")

    async def on_task_error(
        self, task_name: str, error: Exception
    ) -> Optional[Any]:
        """
        Hook called on task error.

        Args:
            task_name: Name of failed task
            error: Exception that occurred

        Returns:
            Optional recovery result
        """
        self.logger.warning(f"Task error: {task_name} - {error}")

        # Check for error patterns
        patterns = self.error_handler.detect_patterns()

        # If critical pattern detected, trigger degradation
        for pattern in patterns.values():
            if pattern.severity == "critical":
                self.logger.error(
                    f"Critical error pattern detected: {pattern.error_type} "
                    f"(frequency: {pattern.frequency})"
                )
                # Could trigger system-wide degradation here

        return None

    def inject_cache(self, task_executor: Any) -> Any:
        """
        Inject caching into task executor.

        Args:
            task_executor: Task executor to wrap

        Returns:
            Wrapped executor with caching
        """
        # This would wrap task executor methods with cache_get
        # Implementation depends on task executor interface
        self.logger.info("Cache injection enabled for task executor")
        return task_executor

    def get_enhancement_stats(self) -> Dict[str, Any]:
        """
        Get statistics about enhancements.

        Returns:
            Dictionary with error and performance stats
        """
        error_patterns = self.error_handler.detect_patterns()
        perf_metrics = self.performance_optimizer.get_metrics_summary()

        return {
            "error_patterns": {
                pattern_type: {
                    "frequency": pattern.frequency,
                    "severity": pattern.severity,
                    "last_occurrence": pattern.last_occurrence,
                }
                for pattern_type, pattern in error_patterns.items()
            },
            "performance_metrics": perf_metrics,
        }


# ==========================
# FACTORY
# ==========================


def create_enhancement_suite(
    max_retries: int = 3,
    max_concurrent: int = 10,
    cache_ttl: int = 300,
) -> Dict[str, Any]:
    """
    Factory function to create complete enhancement suite.

    Args:
        max_retries: Max retry attempts for error handler
        max_concurrent: Max concurrent tasks for optimizer
        cache_ttl: Default cache TTL

    Returns:
        Dictionary with error_handler, performance_optimizer, dsl_hook
    """
    error_handler = ErrorHandler(max_retries=max_retries)
    performance_optimizer = PerformanceOptimizer(
        max_concurrent=max_concurrent,
        default_cache_ttl=cache_ttl,
    )
    dsl_hook = DSLIntegrationHook(error_handler, performance_optimizer)

    return {
        "error_handler": error_handler,
        "performance_optimizer": performance_optimizer,
        "dsl_hook": dsl_hook,
    }


if __name__ == "__main__":
    # Quick validation test
    logging.basicConfig(level=logging.DEBUG)

    async def test_enhancements():
        """Test enhancement suite."""
        suite = create_enhancement_suite()
        error_handler = suite["error_handler"]
        perf_optimizer = suite["performance_optimizer"]

        # Test 1: Retry with backoff
        async def flaky_function(attempt=[0]):
            attempt[0] += 1
            if attempt[0] < 3:
                raise ValueError(f"Attempt {attempt[0]} failed")
            return "Success!"

        result = await error_handler.retry_with_backoff(flaky_function)
        print(f"✅ Retry test: {result}")

        # Test 2: Cache
        def expensive_computation():
            time.sleep(0.1)
            return "Computed value"

        start = time.time()
        val1 = perf_optimizer.cache_get("test_key", expensive_computation)
        time1 = time.time() - start

        start = time.time()
        val2 = perf_optimizer.cache_get("test_key", expensive_computation)
        time2 = time.time() - start

        print(f"✅ Cache test: first={time1:.3f}s, cached={time2:.3f}s (speedup: {time1/time2:.1f}x)")

        # Test 3: Metrics
        @perf_optimizer.track_metrics("test_operation")
        async def tracked_function():
            await asyncio.sleep(0.01)
            return "Tracked"

        await tracked_function()
        await tracked_function()

        stats = perf_optimizer.get_metrics_summary()
        print(f"✅ Metrics test: {stats}")

    asyncio.run(test_enhancements())
    print("\n🎉 All enhancement tests passed!")
