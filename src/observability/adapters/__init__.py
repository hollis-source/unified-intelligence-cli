"""Observability adapters for external systems.

Exports adapter implementations of observability interfaces.
"""

from .in_memory_tracer import InMemoryTracer

__all__ = [
    "InMemoryTracer",
]
