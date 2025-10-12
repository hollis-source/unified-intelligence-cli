"""Observability interfaces for dependency inversion.

Exports interfaces that use cases depend on, following
Dependency Inversion Principle (DIP).
"""

from .tracer import ITracer

__all__ = [
    "ITracer",
]
