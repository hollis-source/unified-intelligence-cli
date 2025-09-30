"""
Dev tools for agent workflows - Simple, focused implementations.

Clean Architecture: Tools are pure functions, no dependencies.
Can be injected into providers that support tool calling.
"""

import subprocess
import os
from pathlib import Path
from typing import Dict, Any, List


# ============================================================================
# Tool Execution Functions
# ============================================================================

def run_command(command: str, cwd: str = ".") -> str:
    """
    Execute a shell command safely.

    Args:
        command: Command to execute
        cwd: Working directory

    Returns:
        Command output or error message
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )

        output = result.stdout if result.stdout else result.stderr
        return output if output else "Command completed with no output"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 30 seconds"
    except Exception as e:
        return f"Error executing command: {str(e)}"


def read_file_content(file_path: str) -> str:
    """
    Read contents of a file.

    Args:
        file_path: Path to file

    Returns:
        File contents or error message
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"Error: File not found: {file_path}"

        if path.stat().st_size > 100000:  # 100KB limit
            return f"Error: File too large (>{100}KB): {file_path}"

        return path.read_text()
    except Exception as e:
        return f"Error reading file: {str(e)}"


def write_file_content(file_path: str, content: str) -> str:
    """
    Write content to a file.

    Args:
        file_path: Path to file
        content: Content to write

    Returns:
        Success or error message
    """
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return f"Successfully wrote {len(content)} characters to {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


def list_files(directory: str = ".", pattern: str = "*") -> str:
    """
    List files in a directory.

    Args:
        directory: Directory to list
        pattern: Glob pattern

    Returns:
        List of files or error message
    """
    try:
        path = Path(directory)
        if not path.exists():
            return f"Error: Directory not found: {directory}"

        if not path.is_dir():
            return f"Error: Not a directory: {directory}"

        files = sorted(path.glob(pattern))
        if not files:
            return f"No files matching '{pattern}' in {directory}"

        file_list = []
        for f in files[:50]:  # Limit to 50 files
            file_type = "DIR" if f.is_dir() else "FILE"
            size = f.stat().st_size if f.is_file() else "-"
            file_list.append(f"{file_type:5} {size:>10} {f.name}")

        return "\n".join(file_list)
    except Exception as e:
        return f"Error listing files: {str(e)}"


# ============================================================================
# Tool Definitions (OpenAI Format)
# ============================================================================

DEV_TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a shell command (git, pytest, npm, etc.)",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute (e.g., 'pytest tests/', 'git status')"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory (default: current directory)"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file_content",
            "description": "Read the contents of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file_content",
            "description": "Write content to a file (creates if doesn't exist)",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["file_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "Directory to list (default: current)"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern (default: *)"
                    }
                },
                "required": []
            }
        }
    }
]


# Tool function registry for execution
TOOL_FUNCTIONS = {
    "run_command": run_command,
    "read_file_content": read_file_content,
    "write_file_content": write_file_content,
    "list_files": list_files
}