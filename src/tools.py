"""
Dev tools for agent workflows - Simple, focused implementations.

Clean Architecture: Tools are pure functions, no dependencies.
Can be injected into providers that support tool calling.

Uses ToolRegistry for extensible tool management (OCP compliance).
"""

import subprocess
import os
import logging
from pathlib import Path
from typing import Dict, Any, List

from src.exceptions import (
    CommandTimeoutError,
    CommandExecutionError,
    FileNotFoundError,
    FileSizeLimitError,
    FileWriteError,
    DirectoryNotFoundError
)
from src.tool_registry import default_registry

# Week 4: Debug logging for tool execution
logger = logging.getLogger(__name__)


# ============================================================================
# Tool Execution Functions
# ============================================================================

def run_command(command: str, cwd: str = ".") -> str:
    """
    Execute a shell command safely.

    Security Note: shell=True is used intentionally for this tool execution context.
    Commands originate from the AI provider (controlled context), not arbitrary user input.
    A 30-second timeout prevents indefinite execution.

    Args:
        command: Command to execute
        cwd: Working directory

    Returns:
        Command output

    Raises:
        CommandTimeoutError: If command exceeds 30s timeout
        CommandExecutionError: If command execution fails
    """
    logger.debug(f"Executing command: {command}")
    logger.debug(f"Working directory: {cwd}")

    try:
        # nosec B602: shell=True is intentional for tool execution.
        # Commands come from AI provider (controlled context), with 30s timeout protection.
        result = subprocess.run(
            command,
            shell=True,  # nosec
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout if result.stdout else result.stderr
        result_output = output if output else "Command completed with no output"

        logger.debug(f"Command exit code: {result.returncode}")
        logger.debug(f"Command output length: {len(result_output)} characters")

        return result_output
    except subprocess.TimeoutExpired:
        logger.debug(f"Command timed out after 30 seconds: {command}")
        raise CommandTimeoutError(command, 30)
    except Exception as e:
        logger.debug(f"Command execution failed: {e}")
        raise CommandExecutionError(command, str(e))


def read_file_content(file_path: str) -> str:
    """
    Read contents of a file.

    Args:
        file_path: Path to file

    Returns:
        File contents

    Raises:
        FileNotFoundError: If file doesn't exist
        FileSizeLimitError: If file exceeds 100KB limit
    """
    logger.debug(f"Reading file: {file_path}")

    path = Path(file_path)
    if not path.exists():
        logger.debug(f"File not found: {file_path}")
        raise FileNotFoundError(file_path)

    size = path.stat().st_size
    limit = 100000  # 100KB

    logger.debug(f"File size: {size} bytes (limit: {limit})")

    if size > limit:
        logger.debug(f"File exceeds size limit: {size} > {limit}")
        raise FileSizeLimitError(file_path, size, limit)

    content = path.read_text()
    logger.debug(f"Successfully read {len(content)} characters from {file_path}")

    return content


def write_file_content(file_path: str, content: str) -> str:
    """
    Write content to a file.

    Args:
        file_path: Path to file
        content: Content to write

    Returns:
        Success message

    Raises:
        FileWriteError: If file write fails
    """
    logger.debug(f"Writing to file: {file_path}")
    logger.debug(f"Content length: {len(content)} characters")

    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

        logger.debug(f"Successfully wrote {len(content)} characters to {file_path}")
        return f"Successfully wrote {len(content)} characters to {file_path}"
    except Exception as e:
        logger.debug(f"File write failed for {file_path}: {e}")
        raise FileWriteError(file_path, str(e))


def _validate_directory_exists(path: Path, directory_name: str) -> None:
    """
    Validate that directory exists and is a directory.

    Args:
        path: Path object to validate
        directory_name: Original directory name (for error message)

    Raises:
        DirectoryNotFoundError: If directory doesn't exist or isn't a directory
    """
    if not path.exists() or not path.is_dir():
        logger.debug(f"Directory not found or not a directory: {directory_name}")
        raise DirectoryNotFoundError(directory_name)


def _format_file_entry(file: Path) -> str:
    """
    Format a single file entry for display.

    Args:
        file: Path object for the file

    Returns:
        Formatted string: "TYPE      SIZE filename"
    """
    file_type = "DIR" if file.is_dir() else "FILE"
    size = file.stat().st_size if file.is_file() else "-"
    return f"{file_type:5} {size:>10} {file.name}"


def _format_files_as_list(files: List[Path], limit: int = 50) -> str:
    """
    Format list of files as formatted string.

    Args:
        files: List of Path objects
        limit: Maximum number of files to include

    Returns:
        Newline-separated formatted file list
    """
    file_list = [_format_file_entry(f) for f in files[:limit]]
    logger.debug(f"Returning {len(file_list)} file entries")
    return "\n".join(file_list)


def list_files(directory: str = ".", pattern: str = "*") -> str:
    """
    List files in a directory.

    Args:
        directory: Directory to list
        pattern: Glob pattern

    Returns:
        List of files (formatted string)

    Raises:
        DirectoryNotFoundError: If directory doesn't exist or isn't a directory
    """
    logger.debug(f"Listing files in directory: {directory}")
    logger.debug(f"Pattern: {pattern}")

    path = Path(directory)
    _validate_directory_exists(path, directory)

    files = sorted(path.glob(pattern))
    logger.debug(f"Found {len(files)} files matching pattern")

    if not files:
        return f"No files matching '{pattern}' in {directory}"

    return _format_files_as_list(files)


# ============================================================================
# Tool Registration (Using Registry Pattern)
# ============================================================================

# Register all tools using the extensible registry
# This follows Open-Closed Principle: extend by adding new registrations,
# no need to modify existing code

default_registry.register_function(
    function=run_command,
    name="run_command",
    description="Execute a shell command (git, pytest, npm, etc.)",
    parameters={
        "command": {
            "type": "string",
            "description": "Shell command to execute (e.g., 'pytest tests/', 'git status')"
        },
        "cwd": {
            "type": "string",
            "description": "Working directory (default: current directory)"
        }
    },
    required=["command"]
)

default_registry.register_function(
    function=read_file_content,
    name="read_file_content",
    description="Read the contents of a file",
    parameters={
        "file_path": {
            "type": "string",
            "description": "Path to the file to read"
        }
    },
    required=["file_path"]
)

default_registry.register_function(
    function=write_file_content,
    name="write_file_content",
    description="Write content to a file (creates if doesn't exist)",
    parameters={
        "file_path": {
            "type": "string",
            "description": "Path to the file to write"
        },
        "content": {
            "type": "string",
            "description": "Content to write to the file"
        }
    },
    required=["file_path", "content"]
)

default_registry.register_function(
    function=list_files,
    name="list_files",
    description="List files in a directory",
    parameters={
        "directory": {
            "type": "string",
            "description": "Directory to list (default: current)"
        },
        "pattern": {
            "type": "string",
            "description": "Glob pattern (default: *)"
        }
    },
    required=[]
)


# ============================================================================
# Backward Compatibility Exports
# ============================================================================

# Export OpenAI-format tools from registry (maintains existing API)
DEV_TOOLS: List[Dict[str, Any]] = default_registry.get_openai_tools()

# Export function registry (maintains existing API)
TOOL_FUNCTIONS: Dict[str, Any] = {
    name: default_registry.get_tool(name)
    for name in default_registry.list_tools()
}