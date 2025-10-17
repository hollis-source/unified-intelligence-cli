from __future__ import annotations

import functools
import asyncio
from typing import Any, Callable, Optional

from src.observability.entities import TraceStatus
from src.observability.interfaces import ITracer

_global_tracer: Optional[ITracer] = None


def set_global_tracer(tracer: ITracer) -> None:
    global _global_tracer
    _global_tracer = tracer


def trace_operation(operation_name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that traces async functions using the global tracer.

    If no global tracer set, it's a no-op wrapper.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                if _global_tracer is None:
                    return await func(*args, **kwargs)
                trace = _global_tracer.start_trace(operation_name)
                try:
                    result = await func(*args, **kwargs)
                    _global_tracer.finish_trace(trace, TraceStatus.SUCCESS)
                    return result
                except Exception as e:
                    _global_tracer.finish_trace(trace, TraceStatus.ERROR, error_message=str(e))
                    raise

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if _global_tracer is None:
                return func(*args, **kwargs)
            trace = _global_tracer.start_trace(operation_name)
            try:
                result = func(*args, **kwargs)
                _global_tracer.finish_trace(trace, TraceStatus.SUCCESS)
                return result
            except Exception as e:
                _global_tracer.finish_trace(trace, TraceStatus.ERROR, error_message=str(e))
                raise

        return sync_wrapper

    return decorator

