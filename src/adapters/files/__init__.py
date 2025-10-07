"""File storage adapters - concrete implementations of IFileStore.

Infrastructure layer: Implements ports defined in use case layer.
"""

from .backend import IFileBackend
from .local_backend import LocalBackend
from .ssh_backend import SSHBackend
from .unified_file_store import UnifiedFileStore

__all__ = ["IFileBackend", "LocalBackend", "SSHBackend", "UnifiedFileStore"]
