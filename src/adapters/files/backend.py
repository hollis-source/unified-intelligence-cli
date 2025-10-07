"""IFileBackend interface - base for concrete file storage backends.

Infrastructure layer: Defines interface for specific storage backends
(LocalBackend, SSHBackend, S3Backend, etc.)
"""

from abc import ABC, abstractmethod
from typing import List

from src.core.entities.file_ref import FileRef


class IFileBackend(ABC):
    """Interface for concrete file storage backends.

    Backends implement transport-specific logic (local filesystem, SSH, S3, etc.).
    UnifiedFileStore routes operations to appropriate backend based on FileRef scheme.

    Responsibilities:
        - Declare which FileRefs it supports (via supports())
        - Implement file operations for its transport

    Example Backends:
        - LocalBackend: file:// → os.path/pathlib
        - SSHBackend: ssh:// → ParamikoSSHAdapter
        - S3Backend: s3:// → boto3
        - GitHubBackend: github:// → GitHub API

    Clean Architecture:
        - Backends are adapters (infrastructure layer)
        - They implement infrastructure-specific logic
        - They are hidden behind UnifiedFileStore (which implements IFileStore port)
    """

    @abstractmethod
    def supports(self, ref: FileRef) -> bool:
        """Check if this backend supports the given FileRef.

        Args:
            ref: FileRef to check

        Returns:
            True if this backend handles this ref's scheme/host

        Example:
            ```python
            class SSHBackend(IFileBackend):
                def supports(self, ref: FileRef) -> bool:
                    return ref.scheme == "ssh"
            ```
        """
        pass

    @abstractmethod
    async def read(self, ref: FileRef) -> str:
        """Read file content.

        Args:
            ref: FileRef (guaranteed to be supported by this backend)

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
        """Write content to file.

        Args:
            ref: FileRef (guaranteed to be supported by this backend)
            content: Content to write

        Raises:
            PermissionError: If access denied
            IOError: For other I/O errors
        """
        pass

    @abstractmethod
    async def exists(self, ref: FileRef) -> bool:
        """Check if file exists.

        Args:
            ref: FileRef (guaranteed to be supported by this backend)

        Returns:
            True if file exists, False otherwise

        Raises:
            PermissionError: If access denied to check existence
            IOError: For other I/O errors
        """
        pass

    @abstractmethod
    async def list_dir(self, ref: FileRef) -> List[FileRef]:
        """List directory contents.

        Args:
            ref: Directory FileRef (guaranteed to be supported by this backend)

        Returns:
            List of FileRef objects for directory contents

        Raises:
            FileNotFoundError: If directory does not exist
            NotADirectoryError: If ref points to a file, not directory
            PermissionError: If access denied
            IOError: For other I/O errors
        """
        pass
