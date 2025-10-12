"""Decorators for automatic tracing instrumentation.

Provides convenient decorators to automatically trace function/method execution
without manual trace management in business logic.
"""

import functools
import asyncio
import inspect
import logging
from typing import Any, Callable, Optional, TypeVar, cast

from .interfaces import ITracer
from .entities import TraceStatus

logger = logging.getLogger(__name__)

# Type variable for generic decorator
F = TypeVar('F', bound=Callable[..., Any])

# Global tracer instance (set by application)
_global_tracer: Optional[ITracer] = None


def set_global_tracer(tracer: ITracer) -> None:
    """Set the global tracer instance.

    Args:
        tracer: Tracer to use for all @trace_operation decorations

    Example:
        >>> from src.observability.adapters import InMemoryTracer
        >>> from src.observability.decorators import set_global_tracer
        >>> set_global_tracer(InMemoryTracer())
    """
    global _global_tracer
    _global_tracer = tracer
    logger.info(f"Global tracer set to {tracer.__class__.__name__}")


def get_global_tracer() -> Optional[ITracer]:
    """Get the global tracer instance.

    Returns:
        Global tracer if set, None otherwise
    """
    return _global_tracer


def trace_operation(operation_name: Optional[str] = None):
    """Decorator to automatically trace function/method execution.

    Supports both synchronous and asynchronous functions.
    Automatically captures:
    - Start/end time
    - Success/failure status
    - Exception details
    - Function arguments as tags

    Args:
        operation_name: Optional operation name (defaults to function name)

    Returns:
        Decorated function

    Example:
        >>> @trace_operation("user.create")
        >>> async def create_user(username: str, email: str):
        >>>     # ...implementation...
        >>>     return user

        >>> @trace_operation()  # Uses function name
        >>> def process_data(data: dict):
        >>>     # ...implementation...
        >>>     return result

    Note:
        Requires global tracer to be set via set_global_tracer().
        If no tracer set, decorator is a no-op (silent pass-through).
    """

    def decorator(func: F) -> F:
        # Get operation name from decorator arg or function name
        op_name = operation_name or f"{func.__module__}.{func.__qualname__}"

        # Check if function is async
        is_async = asyncio.iscoroutinefunction(func)

        if is_async:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                tracer = get_global_tracer()
                if tracer is None:
                    # No tracer set, pass through
                    logger.debug(f"No tracer set for {op_name}, skipping trace")
                    return await func(*args, **kwargs)

                # Extract tags from function signature
                tags = _extract_tags(func, args, kwargs)

                # Start trace
                trace = tracer.start_trace(operation_name=op_name, tags=tags)

                try:
                    # Execute function
                    result = await func(*args, **kwargs)

                    # Finish trace with SUCCESS
                    tracer.finish_trace(trace, TraceStatus.SUCCESS)

                    return result

                except asyncio.TimeoutError as e:
                    # Handle timeout
                    tracer.finish_trace(
                        trace, TraceStatus.TIMEOUT, error_message=f"Timeout: {str(e)}"
                    )
                    raise

                except asyncio.CancelledError as e:
                    # Handle cancellation
                    tracer.finish_trace(
                        trace, TraceStatus.CANCELLED, error_message="Operation cancelled"
                    )
                    raise

                except Exception as e:
                    # Handle error
                    tracer.finish_trace(
                        trace,
                        TraceStatus.ERROR,
                        error_message=f"{type(e).__name__}: {str(e)}",
                    )
                    raise

            return cast(F, async_wrapper)

        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                tracer = get_global_tracer()
                if tracer is None:
                    # No tracer set, pass through
                    logger.debug(f"No tracer set for {op_name}, skipping trace")
                    return func(*args, **kwargs)

                # Extract tags from function signature
                tags = _extract_tags(func, args, kwargs)

                # Start trace
                trace = tracer.start_trace(operation_name=op_name, tags=tags)

                try:
                    # Execute function
                    result = func(*args, **kwargs)

                    # Finish trace with SUCCESS
                    tracer.finish_trace(trace, TraceStatus.SUCCESS)

                    return result

                except Exception as e:
                    # Handle error
                    tracer.finish_trace(
                        trace,
                        TraceStatus.ERROR,
                        error_message=f"{type(e).__name__}: {str(e)}",
                    )
                    raise

            return cast(F, sync_wrapper)

    return decorator


def _extract_tags(func: Callable, args: tuple, kwargs: dict) -> dict[str, str]:
    """Extract function arguments as trace tags.

    Args:
        func: Function being traced
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        Dictionary of tags (argument_name -> str(value))

    Note:
        - Limits tag values to first 100 characters
        - Skips 'self' and 'cls' arguments
        - Converts all values to strings
    """
    tags = {}

    try:
        # Get function signature
        sig = inspect.signature(func)
        bound_args = sig.bind_partial(*args, **kwargs)
        bound_args.apply_defaults()

        # Extract argument values as tags
        for param_name, param_value in bound_args.arguments.items():
            # Skip self/cls
            if param_name in ("self", "cls"):
                continue

            # Convert to string and limit length
            tag_value = str(param_value)
            if len(tag_value) > 100:
                tag_value = tag_value[:97] + "..."

            tags[f"arg.{param_name}"] = tag_value

    except Exception as e:
        # If tag extraction fails, log but don't crash
        logger.warning(f"Failed to extract tags from {func.__name__}: {e}")

    return tags
