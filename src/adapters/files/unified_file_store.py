"""UnifiedFileStore - routes file operations to the appropriate backend.

Implements the IFileStore port by delegating to a list of IFileBackend
adapters based on which backend supports a given FileRef.

Errors from backends (FileNotFoundError, PermissionError, NotADirectoryError,
IOError) are intentionally allowed to propagate to callers.
"""

from typing import List

from src.core.ports.file_store import IFileStore
from src.adapters.files.backend import IFileBackend
from src.core.entities.file_ref import FileRef


class UnifiedFileStore(IFileStore):
    """Unified file store that delegates to registered backends.

    Selection strategy: first backend whose `supports(ref)` returns True.
    """

    def __init__(self, backends: List[IFileBackend]):
        self._backends: List[IFileBackend] = list(backends)

    def _get_backend(self, ref: FileRef) -> IFileBackend:
        """Return the first backend that supports the given FileRef.

        Raises:
            ValueError: If no registered backend supports the ref
        """
        for backend in self._backends:
            if backend.supports(ref):
                return backend
        raise ValueError(
            f"No file backend supports ref: scheme={ref.scheme!r}, host={ref.host!r}, path={ref.path!r}"
        )

    async def read(self, ref: FileRef) -> str:
        """Read file content from the appropriate backend.

        Propagates FileNotFoundError, PermissionError, IOError from backend.
        """
        backend = self._get_backend(ref)
        return await backend.read(ref)

    async def write(self, ref: FileRef, content: str) -> None:
        """Write content to file using the appropriate backend.

        Propagates PermissionError, IOError from backend.
        """
        backend = self._get_backend(ref)
        await backend.write(ref, content)

    async def exists(self, ref: FileRef) -> bool:
        """Check existence using the appropriate backend.

        Propagates PermissionError, IOError from backend.
        """
        backend = self._get_backend(ref)
        return await backend.exists(ref)

    async def list_dir(self, ref: FileRef):
        """List directory contents using the appropriate backend.

        Propagates FileNotFoundError, NotADirectoryError, PermissionError, IOError.
        """
        backend = self._get_backend(ref)
        return await backend.list_dir(ref)

