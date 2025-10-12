"""IFileStore port - abstraction for file operations.

Clean Architecture: Port/Interface at use case boundary.
Use cases depend on this abstraction, not concrete file backends.
Follows Dependency Inversion Principle (DIP).
"""

from abc import ABC, abstractmethod
from typing import List

from src.core.entities.file_ref import FileRef


class IFileStore(ABC):
    """Port for all file operations across storage backends.

    Defines the interface that use cases depend on for file I/O.
    Concrete implementations (UnifiedFileStore, MockFileStore) implement
    this interface, allowing use cases to remain independent of infrastructure.

    Clean Architecture Principle:
        - Use cases depend on IFileStore (abstraction)
        - Infrastructure adapters implement IFileStore
        - Direction of dependency: Infrastructure → Use Cases (DIP)

    Supported Operations:
        - read: Fetch file content
        - write: Store file content
        - exists: Check file existence
        - list_dir: List directory contents

    All operations are async to support I/O-bound backends (SSH, S3, HTTP).
    All operations work with FileRef for backend-agnostic file references.

    Example:
        ```python
        file_store: IFileStore = UnifiedFileStore(...)
        ref = FileRef.parse("ssh://host/opt/app.py")

        if await file_store.exists(ref):
            content = await file_store.read(ref)
            # Process content
            await file_store.write(ref, modified_content)
        ```
    """

    @abstractmethod
    async def read(self, ref: FileRef) -> str:
        """Read file content from storage backend.

        Args:
            ref: File reference (local, SSH, S3, etc.)

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If file does not exist
            PermissionError: If access denied
            IOError: For other I/O errors
        """
        pass

    @abstractmethod
    async def write(self, ref: FileRef, content: str) -> None:
        """Write content to file on storage backend.

        Creates file if it doesn't exist, overwrites if it does.

        Args:
            ref: File reference (local, SSH, S3, etc.)
            content: Content to write (string)

        Raises:
            PermissionError: If access denied
            IOError: For other I/O errors
        """
        pass

    @abstractmethod
    async def exists(self, ref: FileRef) -> bool:
        """Check if file exists on storage backend.

        Args:
            ref: File reference to check

        Returns:
            True if file exists, False otherwise

        Raises:
            PermissionError: If access denied to check existence
            IOError: For other I/O errors
        """
        pass

    @abstractmethod
    async def list_dir(self, ref: FileRef) -> List[FileRef]:
        """List contents of directory.

        Args:
            ref: Directory reference to list

        Returns:
            List of FileRef objects for directory contents

        Raises:
            FileNotFoundError: If directory does not exist
            NotADirectoryError: If ref points to a file, not directory
            PermissionError: If access denied
            IOError: For other I/O errors
        """
        pass
