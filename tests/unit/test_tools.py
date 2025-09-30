"""Unit tests for dev tools (tools.py)."""

import pytest
from pathlib import Path
import subprocess

from src.tools import (
    run_command,
    read_file_content,
    write_file_content,
    list_files
)
from src.exceptions import (
    CommandTimeoutError,
    CommandExecutionError,
    FileNotFoundError,
    FileSizeLimitError,
    FileWriteError,
    DirectoryNotFoundError
)


class TestRunCommand:
    """Test run_command tool function."""

    def test_run_command_success(self):
        """Test successful command execution."""
        result = run_command("echo 'Hello World'")
        assert "Hello World" in result

    def test_run_command_with_cwd(self, tmp_path):
        """Test command with custom working directory."""
        # Create test directory and file
        test_dir = tmp_path / "test_cwd"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        result = run_command("ls", cwd=str(test_dir))
        assert "file.txt" in result

    def test_run_command_timeout(self):
        """Test that long-running command raises timeout error."""
        with pytest.raises(CommandTimeoutError) as exc_info:
            run_command("sleep 35")  # Exceeds 30s timeout

        assert exc_info.value.command == "sleep 35"
        assert exc_info.value.timeout == 30
        assert "timed out after 30s" in str(exc_info.value)

    def test_run_command_invalid(self):
        """Test that invalid command returns error in output."""
        result = run_command("nonexistent_command_xyz")

        # Shell returns error message (not found), doesn't raise exception
        assert "not found" in result.lower() or "nonexistent" in result.lower()

    def test_run_command_no_output(self):
        """Test command with no output."""
        result = run_command("true")  # Returns success but no output
        assert "Command completed with no output" in result


class TestReadFileContent:
    """Test read_file_content tool function."""

    def test_read_file_success(self, tmp_path):
        """Test successful file read."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello from file")

        result = read_file_content(str(test_file))
        assert result == "Hello from file"

    def test_read_file_not_found(self):
        """Test reading nonexistent file raises error."""
        with pytest.raises(FileNotFoundError) as exc_info:
            read_file_content("/nonexistent/file.txt")

        assert exc_info.value.file_path == "/nonexistent/file.txt"
        assert "/nonexistent/file.txt" in str(exc_info.value)

    def test_read_file_too_large(self, tmp_path):
        """Test reading file exceeding size limit raises error."""
        test_file = tmp_path / "large.txt"
        # Create file larger than 100KB limit
        large_content = "x" * 150000  # 150KB
        test_file.write_text(large_content)

        with pytest.raises(FileSizeLimitError) as exc_info:
            read_file_content(str(test_file))

        assert exc_info.value.file_path == str(test_file)
        assert exc_info.value.size == 150000
        assert exc_info.value.limit == 100000
        assert "too large" in str(exc_info.value).lower()


class TestWriteFileContent:
    """Test write_file_content tool function."""

    def test_write_file_success(self, tmp_path):
        """Test successful file write."""
        test_file = tmp_path / "output.txt"
        content = "Test content for writing"

        result = write_file_content(str(test_file), content)

        assert "Successfully wrote" in result
        assert "24 characters" in result  # len(content)
        assert test_file.read_text() == content

    def test_write_file_creates_parent_dirs(self, tmp_path):
        """Test that write creates parent directories."""
        nested_file = tmp_path / "nested" / "deep" / "file.txt"
        content = "Nested content"

        result = write_file_content(str(nested_file), content)

        assert "Successfully wrote" in result
        assert nested_file.exists()
        assert nested_file.read_text() == content

    def test_write_file_overwrites(self, tmp_path):
        """Test that write overwrites existing file."""
        test_file = tmp_path / "existing.txt"
        test_file.write_text("Old content")

        result = write_file_content(str(test_file), "New content")

        assert "Successfully wrote" in result
        assert test_file.read_text() == "New content"

    def test_write_file_to_invalid_path(self):
        """Test writing to invalid path raises error."""
        # Try to write to root (permission denied)
        with pytest.raises(FileWriteError) as exc_info:
            write_file_content("/root/forbidden.txt", "content")

        assert exc_info.value.file_path == "/root/forbidden.txt"


class TestListFiles:
    """Test list_files tool function."""

    def test_list_files_default(self, tmp_path):
        """Test listing files in directory."""
        # Create test files
        (tmp_path / "file1.txt").write_text("1")
        (tmp_path / "file2.py").write_text("2")
        (tmp_path / "subdir").mkdir()

        result = list_files(str(tmp_path))

        assert "file1.txt" in result
        assert "file2.py" in result
        assert "subdir" in result
        assert "FILE" in result
        assert "DIR" in result

    def test_list_files_with_pattern(self, tmp_path):
        """Test listing files with glob pattern."""
        # Create test files
        (tmp_path / "test.py").write_text("py")
        (tmp_path / "test.txt").write_text("txt")
        (tmp_path / "readme.md").write_text("md")

        result = list_files(str(tmp_path), pattern="*.py")

        assert "test.py" in result
        assert "test.txt" not in result
        assert "readme.md" not in result

    def test_list_files_empty_directory(self, tmp_path):
        """Test listing empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        result = list_files(str(empty_dir))

        assert "No files matching" in result

    def test_list_files_nonexistent_directory(self):
        """Test listing nonexistent directory raises error."""
        with pytest.raises(DirectoryNotFoundError) as exc_info:
            list_files("/nonexistent/directory")

        assert exc_info.value.directory == "/nonexistent/directory"
        assert "/nonexistent/directory" in str(exc_info.value)

    def test_list_files_not_a_directory(self, tmp_path):
        """Test listing a file (not directory) raises error."""
        test_file = tmp_path / "not_a_dir.txt"
        test_file.write_text("content")

        with pytest.raises(DirectoryNotFoundError) as exc_info:
            list_files(str(test_file))

        assert exc_info.value.directory == str(test_file)