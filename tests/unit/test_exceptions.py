"""Unit tests for custom exceptions."""

import pytest

from src.exceptions import (
    ToolExecutionError,
    CommandTimeoutError,
    FileSizeLimitError,
    FileNotFoundError,
    DirectoryNotFoundError,
    CommandExecutionError,
    FileWriteError
)


class TestToolExecutionError:
    """Test base exception class."""

    def test_base_exception(self):
        """Test base ToolExecutionError."""
        error = ToolExecutionError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert isinstance(error, Exception)


class TestCommandTimeoutError:
    """Test command timeout exception."""

    def test_timeout_error_attributes(self):
        """Test CommandTimeoutError has correct attributes."""
        error = CommandTimeoutError("long_command --arg", 30)

        assert error.command == "long_command --arg"
        assert error.timeout == 30
        assert "timed out after 30s" in str(error)
        assert "long_command" in str(error)

    def test_timeout_error_long_command(self):
        """Test timeout error truncates long commands."""
        long_cmd = "x" * 200
        error = CommandTimeoutError(long_cmd, 60)

        # Should truncate command in message
        assert len(str(error)) < 200
        assert "timed out after 60s" in str(error)

    def test_timeout_error_inherits_from_tool_error(self):
        """Test CommandTimeoutError inherits from ToolExecutionError."""
        error = CommandTimeoutError("cmd", 30)
        assert isinstance(error, ToolExecutionError)


class TestFileSizeLimitError:
    """Test file size limit exception."""

    def test_file_size_error_attributes(self):
        """Test FileSizeLimitError has correct attributes."""
        error = FileSizeLimitError("large.bin", 200000, 100000)

        assert error.file_path == "large.bin"
        assert error.size == 200000
        assert error.limit == 100000
        assert "large.bin" in str(error)
        assert "MB" in str(error)  # Should show size in MB

    def test_file_size_error_conversion_to_mb(self):
        """Test file sizes are displayed in MB."""
        error = FileSizeLimitError("test.bin", 150 * 1024 * 1024, 100 * 1024 * 1024)

        error_msg = str(error)
        assert "150" in error_msg  # 150 MB
        assert "100" in error_msg  # 100 MB limit
        assert "MB" in error_msg

    def test_file_size_error_inherits_from_tool_error(self):
        """Test FileSizeLimitError inherits from ToolExecutionError."""
        error = FileSizeLimitError("file", 1000, 500)
        assert isinstance(error, ToolExecutionError)


class TestFileNotFoundError:
    """Test file not found exception."""

    def test_file_not_found_attributes(self):
        """Test FileNotFoundError has correct attributes."""
        error = FileNotFoundError("/path/to/missing.txt")

        assert error.file_path == "/path/to/missing.txt"
        assert "File not found" in str(error)
        assert "/path/to/missing.txt" in str(error)

    def test_file_not_found_inherits_from_tool_error(self):
        """Test FileNotFoundError inherits from ToolExecutionError."""
        error = FileNotFoundError("missing.txt")
        assert isinstance(error, ToolExecutionError)


class TestDirectoryNotFoundError:
    """Test directory not found exception."""

    def test_directory_not_found_attributes(self):
        """Test DirectoryNotFoundError has correct attributes."""
        error = DirectoryNotFoundError("/path/to/missing/")

        assert error.directory == "/path/to/missing/"
        assert "Directory not found" in str(error)
        assert "/path/to/missing/" in str(error)

    def test_directory_not_found_inherits_from_tool_error(self):
        """Test DirectoryNotFoundError inherits from ToolExecutionError."""
        error = DirectoryNotFoundError("/missing")
        assert isinstance(error, ToolExecutionError)


class TestCommandExecutionError:
    """Test command execution exception."""

    def test_command_execution_error_attributes(self):
        """Test CommandExecutionError has correct attributes."""
        error = CommandExecutionError("git status", "fatal: not a git repository")

        assert error.command == "git status"
        assert error.error == "fatal: not a git repository"
        assert "Command execution failed" in str(error)
        assert "fatal: not a git repository" in str(error)

    def test_command_execution_error_inherits_from_tool_error(self):
        """Test CommandExecutionError inherits from ToolExecutionError."""
        error = CommandExecutionError("cmd", "error")
        assert isinstance(error, ToolExecutionError)


class TestFileWriteError:
    """Test file write exception."""

    def test_file_write_error_attributes(self):
        """Test FileWriteError has correct attributes."""
        error = FileWriteError("/readonly/file.txt", "Permission denied")

        assert error.file_path == "/readonly/file.txt"
        assert error.error == "Permission denied"
        assert "Failed to write file" in str(error)
        assert "/readonly/file.txt" in str(error)
        assert "Permission denied" in str(error)

    def test_file_write_error_inherits_from_tool_error(self):
        """Test FileWriteError inherits from ToolExecutionError."""
        error = FileWriteError("file.txt", "error")
        assert isinstance(error, ToolExecutionError)


class TestExceptionCatching:
    """Test that exceptions can be caught properly."""

    def test_catch_specific_exception(self):
        """Test catching specific exception types."""
        with pytest.raises(CommandTimeoutError) as exc_info:
            raise CommandTimeoutError("cmd", 30)

        assert exc_info.value.timeout == 30

    def test_catch_base_exception(self):
        """Test catching base ToolExecutionError catches all tool errors."""
        with pytest.raises(ToolExecutionError):
            raise CommandTimeoutError("cmd", 30)

        with pytest.raises(ToolExecutionError):
            raise FileSizeLimitError("file", 1000, 500)

        with pytest.raises(ToolExecutionError):
            raise FileNotFoundError("missing.txt")