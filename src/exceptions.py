"""
Custom exceptions for unified-intelligence-cli.

Clean Code: Explicit error handling with meaningful exception types.
Week 1: Enhanced with error_details conversion for better debugging.
"""

from typing import Dict, Any


class ToolExecutionError(Exception):
    """
    Base exception for tool execution errors.

    Enhanced with to_error_details() for structured error reporting.
    """

    def to_error_details(self) -> Dict[str, Any]:
        """
        Convert exception to error_details dict.

        Returns structured error information for ExecutionResult.
        Subclasses should override to add specific context.
        """
        return {
            "error_type": "ToolError",
            "component": "tool_execution",
            "root_cause": str(self),
            "user_message": str(self),
            "suggestion": "Check tool input parameters and try again. Use --verbose for more details.",
            "context": {
                "exception_class": self.__class__.__name__
            }
        }


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

    def to_error_details(self) -> Dict[str, Any]:
        """Convert to structured error_details."""
        return {
            "error_type": "ToolError",
            "component": "run_command",
            "input": {"command": self.command, "timeout": self.timeout},
            "root_cause": f"Command execution exceeded {self.timeout}s timeout",
            "user_message": f"Command timed out after {self.timeout} seconds: {self.command[:50]}{'...' if len(self.command) > 50 else ''}",
            "suggestion": f"The command took longer than {self.timeout}s. Try breaking it into smaller steps or increase timeout if needed.",
            "context": {
                "command": self.command,
                "timeout_seconds": self.timeout,
                "tool": "run_command"
            }
        }


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

    def to_error_details(self) -> Dict[str, Any]:
        """Convert to structured error_details."""
        size_mb = self.size / (1024 * 1024)
        limit_mb = self.limit / (1024 * 1024)
        return {
            "error_type": "ToolError",
            "component": "read_file_content",
            "input": {"file_path": self.file_path},
            "root_cause": f"File size ({size_mb:.2f}MB) exceeds limit ({limit_mb:.2f}MB)",
            "user_message": f"File is too large to read: {self.file_path} ({size_mb:.2f}MB exceeds {limit_mb:.2f}MB limit)",
            "suggestion": "The file exceeds the maximum size for reading. Consider reading it in chunks or processing a smaller file.",
            "context": {
                "file_path": self.file_path,
                "size_bytes": self.size,
                "size_mb": round(size_mb, 2),
                "limit_bytes": self.limit,
                "limit_mb": round(limit_mb, 2),
                "tool": "read_file_content"
            }
        }


class FileNotFoundError(ToolExecutionError):
    """
    Raised when a required file is not found.

    Attributes:
        file_path: Path to the missing file
    """

    def __init__(self, file_path: str):
        self.file_path = file_path
        super().__init__(f"File not found: {file_path}")

    def to_error_details(self) -> Dict[str, Any]:
        """Convert to structured error_details."""
        return {
            "error_type": "ToolError",
            "component": "read_file_content",
            "input": {"file_path": self.file_path},
            "root_cause": f"File does not exist at path: {self.file_path}",
            "user_message": f"File not found: {self.file_path}",
            "suggestion": "Check that the file path is correct and the file exists. Use list_files to browse available files.",
            "context": {
                "file_path": self.file_path,
                "tool": "read_file_content"
            }
        }


class DirectoryNotFoundError(ToolExecutionError):
    """
    Raised when a required directory is not found.

    Attributes:
        directory: Path to the missing directory
    """

    def __init__(self, directory: str):
        self.directory = directory
        super().__init__(f"Directory not found: {directory}")

    def to_error_details(self) -> Dict[str, Any]:
        """Convert to structured error_details."""
        return {
            "error_type": "ToolError",
            "component": "list_files",
            "input": {"directory": self.directory},
            "root_cause": f"Directory does not exist or is not accessible: {self.directory}",
            "user_message": f"Directory not found: {self.directory}",
            "suggestion": "Check that the directory path is correct. Use list_files on parent directory to see available directories.",
            "context": {
                "directory": self.directory,
                "tool": "list_files"
            }
        }


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

    def to_error_details(self) -> Dict[str, Any]:
        """Convert to structured error_details."""
        return {
            "error_type": "ToolError",
            "component": "run_command",
            "input": {"command": self.command},
            "root_cause": f"Command execution failed: {self.error}",
            "user_message": f"Command failed: {self.command[:50]}{'...' if len(self.command) > 50 else ''}\nError: {self.error}",
            "suggestion": "Check the command syntax and ensure all required dependencies are available.",
            "context": {
                "command": self.command,
                "error": self.error,
                "tool": "run_command"
            }
        }


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

    def to_error_details(self) -> Dict[str, Any]:
        """Convert to structured error_details."""
        return {
            "error_type": "ToolError",
            "component": "write_file_content",
            "input": {"file_path": self.file_path},
            "root_cause": f"File write operation failed: {self.error}",
            "user_message": f"Failed to write to file: {self.file_path}\nError: {self.error}",
            "suggestion": "Check file permissions, disk space, and that the parent directory exists.",
            "context": {
                "file_path": self.file_path,
                "error": self.error,
                "tool": "write_file_content"
            }
        }