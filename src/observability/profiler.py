"""Performance Profiling and Error Tracking Hooks.

Sprint 1: Production Deployment - P1.3 Observability
Provides decorators for performance profiling and error tracking.

Clean Architecture: Use case layer (observability concern).
SOLID: SRP - Single responsibility for profiling and error tracking.
"""

import time
import logging
import functools
import threading
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for a function."""
    function_name: str
    call_count: int = 0
    error_count: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: Optional[float] = None
    max_duration_ms: Optional[float] = None
    last_error: Optional[str] = None
    last_error_time: Optional[float] = None


class PerformanceProfiler:
    """Tracks performance metrics and errors for instrumented functions.

    Thread-safe for concurrent access.
    Provides Prometheus-formatted metrics export.
    """

    def __init__(self):
        """Initialize performance profiler."""
        self._lock = threading.RLock()
        self._metrics: Dict[str, PerformanceMetrics] = {}

    def record_call(
        self,
        function_name: str,
        duration_ms: float,
        error: Optional[str] = None
    ) -> None:
        """Record a function call with performance data.

        Args:
            function_name: Name of the function
            duration_ms: Execution duration in milliseconds
            error: Optional error message if call failed
        """
        with self._lock:
            if function_name not in self._metrics:
                self._metrics[function_name] = PerformanceMetrics(function_name=function_name)

            metrics = self._metrics[function_name]
            metrics.call_count += 1
            metrics.total_duration_ms += duration_ms

            # Update min/max
            if metrics.min_duration_ms is None or duration_ms < metrics.min_duration_ms:
                metrics.min_duration_ms = duration_ms
            if metrics.max_duration_ms is None or duration_ms > metrics.max_duration_ms:
                metrics.max_duration_ms = duration_ms

            # Track errors
            if error:
                metrics.error_count += 1
                metrics.last_error = error
                metrics.last_error_time = time.time()

    def get_metrics(self, function_name: Optional[str] = None) -> Dict:
        """Get performance metrics.

        Args:
            function_name: Optional function name to get specific metrics

        Returns:
            Dictionary with performance metrics
        """
        with self._lock:
            if function_name:
                metrics = self._metrics.get(function_name)
                if not metrics:
                    return {}

                avg_duration = metrics.total_duration_ms / max(metrics.call_count, 1)
                error_rate = metrics.error_count / max(metrics.call_count, 1)

                return {
                    "function": metrics.function_name,
                    "call_count": metrics.call_count,
                    "error_count": metrics.error_count,
                    "error_rate": round(error_rate, 4),
                    "avg_duration_ms": round(avg_duration, 2),
                    "min_duration_ms": round(metrics.min_duration_ms or 0, 2),
                    "max_duration_ms": round(metrics.max_duration_ms or 0, 2),
                    "total_duration_ms": round(metrics.total_duration_ms, 2),
                    "last_error": metrics.last_error,
                }
            else:
                # Return all metrics
                return {
                    fn: self.get_metrics(fn)
                    for fn in self._metrics.keys()
                }

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format.

        Returns:
            Prometheus-formatted metrics string
        """
        with self._lock:
            lines = []

            # Function call counts
            lines.extend([
                "# HELP function_calls_total Total function calls",
                "# TYPE function_calls_total counter",
            ])
            for func_name, metrics in self._metrics.items():
                safe_name = func_name.replace(".", "_").replace("-", "_")
                lines.append(f'function_calls_total{{function="{safe_name}"}} {metrics.call_count}')
            lines.append("")

            # Error counts
            lines.extend([
                "# HELP function_errors_total Total function errors",
                "# TYPE function_errors_total counter",
            ])
            for func_name, metrics in self._metrics.items():
                safe_name = func_name.replace(".", "_").replace("-", "_")
                lines.append(f'function_errors_total{{function="{safe_name}"}} {metrics.error_count}')
            lines.append("")

            # Error rates
            lines.extend([
                "# HELP function_error_rate Function error rate",
                "# TYPE function_error_rate gauge",
            ])
            for func_name, metrics in self._metrics.items():
                safe_name = func_name.replace(".", "_").replace("-", "_")
                error_rate = metrics.error_count / max(metrics.call_count, 1)
                lines.append(f'function_error_rate{{function="{safe_name}"}} {error_rate:.4f}')
            lines.append("")

            # Average duration
            lines.extend([
                "# HELP function_duration_ms_avg Average function duration in milliseconds",
                "# TYPE function_duration_ms_avg gauge",
            ])
            for func_name, metrics in self._metrics.items():
                safe_name = func_name.replace(".", "_").replace("-", "_")
                avg_duration = metrics.total_duration_ms / max(metrics.call_count, 1)
                lines.append(f'function_duration_ms_avg{{function="{safe_name}"}} {avg_duration:.2f}')
            lines.append("")

            # Max duration
            lines.extend([
                "# HELP function_duration_ms_max Maximum function duration in milliseconds",
                "# TYPE function_duration_ms_max gauge",
            ])
            for func_name, metrics in self._metrics.items():
                safe_name = func_name.replace(".", "_").replace("-", "_")
                max_duration = metrics.max_duration_ms or 0
                lines.append(f'function_duration_ms_max{{function="{safe_name}"}} {max_duration:.2f}')
            lines.append("")

            return "\n".join(lines)


# Global singleton instance
_global_profiler: Optional[PerformanceProfiler] = None
_profiler_lock = threading.Lock()


def get_profiler() -> PerformanceProfiler:
    """Get global performance profiler instance (singleton).

    Returns:
        Global PerformanceProfiler instance
    """
    global _global_profiler

    with _profiler_lock:
        if _global_profiler is None:
            _global_profiler = PerformanceProfiler()
        return _global_profiler


def profile_performance(func: Optional[Callable] = None, *, name: Optional[str] = None):
    """Decorator to profile function performance and errors.

    Usage:
        @profile_performance
        def my_function():
            ...

        @profile_performance(name="custom_name")
        def another_function():
            ...

    Args:
        func: Function to decorate (when used without parentheses)
        name: Optional custom name for metrics (defaults to function name)

    Returns:
        Decorated function
    """
    def decorator(f: Callable) -> Callable:
        func_name = name or f"{f.__module__}.{f.__name__}"
        profiler = get_profiler()

        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            error = None

            try:
                result = f(*args, **kwargs)
                return result
            except Exception as e:
                error = f"{type(e).__name__}: {str(e)}"
                logger.error(f"Error in {func_name}: {error}")
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                profiler.record_call(func_name, duration_ms, error)

        return wrapper

    # Handle both @profile_performance and @profile_performance()
    if func is None:
        # Called with parentheses: @profile_performance()
        return decorator
    else:
        # Called without parentheses: @profile_performance
        return decorator(func)


def track_error(
    error: Exception,
    context: Optional[str] = None,
    severity: str = "error"
) -> None:
    """Track an error for monitoring and alerting.

    Args:
        error: Exception instance
        context: Optional context description
        severity: Error severity (error, warning, critical)
    """
    error_msg = f"{type(error).__name__}: {str(error)}"

    if context:
        error_msg = f"{context} - {error_msg}"

    # Log based on severity
    if severity == "critical":
        logger.critical(error_msg)
    elif severity == "warning":
        logger.warning(error_msg)
    else:
        logger.error(error_msg)

    # Record in profiler (use context as function name if provided)
    profiler = get_profiler()
    func_name = context or "uncategorized_error"
    profiler.record_call(func_name, 0, error_msg)
