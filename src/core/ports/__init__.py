"""Ports (interfaces) for Clean Architecture boundary.

Ports define the interface between use cases and infrastructure.
Use cases depend on ports, not concrete implementations (Dependency Inversion).
"""

from .file_store import IFileStore

__all__ = ["IFileStore"]
