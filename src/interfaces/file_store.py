"""IFileStore Port - Abstract interface for file operations.

Clean Architecture: Port/Interface at use case layer.
SOLID: ISP - Interface segregation, DIP - Dependency inversion.

This port defines the abstraction for all file operations. Use cases depend on
this interface, not on concrete implementations. This allows swapping storage
backends (local, SSH, S3, etc.) without changing business logic.

The port pattern (Hexagonal Architecture) ensures that:
1. Use cases remain independent of infrastructure details
2. Storage backends can be swapped without touching use cases
3. Testing is simplified via mock implementations
4. New backends can be added without modifying existing code (OCP)
"""

from abc import ABC, abstractmethod
from typing import List
from src.entities.file_ref import FileRef


class IFileStore(ABC):
    """Port for all file operations across different storage backends.

    This interface defines the contract that all file storage implementations
    must fulfill. Use cases depend on this abstraction, not on concrete
    implementations like LocalFileStore or SSHFileStore.

    All methods are async to support I/O-bound operations efficiently.

    Design Principles:
        - DIP: Use cases depend on this abstraction, not concrete adapters
        - ISP: Minimal interface with only essential operations
        - OCP: New backends can be added without modifying this interface
        - SRP: Single responsibility of file I/O operations

    Examples:
        >>> # Use case depends on abstraction
        >>> class ResourceResolver:
        ...     def __init__(self, file_store: IFileStore):
        ...         self.file_store = file_store
        ...
        ...     async def load_file(self, ref: FileRef) -> str:
        ...         return await self.file_store.read(ref)

        >>> # Concrete implementation injected at runtime
        >>> file_store = UnifiedFileStore([LocalBackend(), SSHBackend()])
        >>> resolver = ResourceResolver(file_store)
    """

    @abstractmethod
    async def read(self, ref: FileRef) -> str:
        """Read file content from storage backend.

        Args:
            ref: FileRef identifying the file to read

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If file does not exist
            PermissionError: If access is denied
            IOError: If read operation fails

        Examples:
            >>> ref = FileRef.parse("file:///home/user/app.py")
            >>> content = await file_store.read(ref)
            >>> print(content)
            'def main(): ...'
        """
        pass

    @abstractmethod
    async def write(self, ref: FileRef, content: str) -> None:
        """Write content to file in storage backend.

        Creates the file if it doesn't exist, overwrites if it does.
        Parent directories are created automatically if needed.

        Args:
            ref: FileRef identifying the file to write
            content: String content to write

        Raises:
            PermissionError: If write access is denied
            IOError: If write operation fails

        Examples:
            >>> ref = FileRef.parse("file:///home/user/output.txt")
            >>> await file_store.write(ref, "Hello, World!")
        """
        pass

    @abstractmethod
    async def exists(self, ref: FileRef) -> bool:
        """Check if file exists in storage backend.

        Args:
            ref: FileRef identifying the file to check

        Returns:
            True if file exists, False otherwise

        Raises:
            PermissionError: If access to check existence is denied
            IOError: If existence check fails

        Examples:
            >>> ref = FileRef.parse("ssh://host/opt/app.py")
            >>> if await file_store.exists(ref):
            ...     content = await file_store.read(ref)
        """
        pass

    @abstractmethod
    async def list_dir(self, ref: FileRef) -> List[FileRef]:
        """List directory contents in storage backend.

        Args:
            ref: FileRef identifying the directory to list

        Returns:
            List of FileRef objects for each file/directory in the directory

        Raises:
            FileNotFoundError: If directory does not exist
            NotADirectoryError: If ref points to a file, not a directory
            PermissionError: If access is denied
            IOError: If list operation fails

        Examples:
            >>> dir_ref = FileRef.parse("file:///home/user/project")
            >>> files = await file_store.list_dir(dir_ref)
            >>> for file_ref in files:
            ...     print(file_ref.path)
            '/home/user/project/app.py'
            '/home/user/project/test.py'
        """
        pass

