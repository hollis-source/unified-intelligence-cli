"""
Custom exceptions for unified-intelligence-cli.

Clean Code: Explicit error handling with meaningful exception types.
"""


class ToolExecutionError(Exception):
    """Base exception for tool execution errors."""
    pass


class CommandTimeoutError(ToolExecutionError):
    """
    Raised when a command exceeds its timeout limit.

    Attributes:
        command: The command that timed out
        timeout: The timeout value in seconds
    """

    def __init__(self, command: str, timeout: int):
        self.command = command
        self.timeout = timeout
        super().__init__(f"Command timed out after {timeout}s: {command[:100]}")


class FileSizeLimitError(ToolExecutionError):
    """
    Raised when a file exceeds the size limit.

    Attributes:
        file_path: Path to the file
        size: Actual size in bytes
        limit: Maximum allowed size in bytes
    """

    def __init__(self, file_path: str, size: int, limit: int):
        self.file_path = file_path
        self.size = size
        self.limit = limit
        size_mb = size / (1024 * 1024)
        limit_mb = limit / (1024 * 1024)
        super().__init__(
            f"File too large: {file_path} ({size_mb:.2f}MB exceeds {limit_mb:.2f}MB limit)"
        )


class FileNotFoundError(ToolExecutionError):
    """
    Raised when a required file is not found.

    Attributes:
        file_path: Path to the missing file
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        super().__init__(f"File not found: {file_path}")


class DirectoryNotFoundError(ToolExecutionError):
    """
    Raised when a required directory is not found.

    Attributes:
        directory: Path to the missing directory
    """

    def __init__(self, directory: str):
        self.directory = directory
        super().__init__(f"Directory not found: {directory}")


class CommandExecutionError(ToolExecutionError):
    """
    Raised when a command fails to execute.

    Attributes:
        command: The command that failed
        error: The underlying error message
    """

    def __init__(self, command: str, error: str):
        self.command = command
        self.error = error
        super().__init__(f"Command execution failed: {error}")


class FileWriteError(ToolExecutionError):
    """
    Raised when writing to a file fails.

    Attributes:
        file_path: Path where write was attempted
        error: The underlying error message
    """

    def __init__(self, file_path: str, error: str):
        self.file_path = file_path
        self.error = error
        super().__init__(f"Failed to write file {file_path}: {error}")