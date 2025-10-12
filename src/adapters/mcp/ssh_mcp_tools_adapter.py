"""
SSH MCP Tools Adapter for Project Builder

Uses Claude Code's MCP tools for remote file operations.
This adapter delegates to the MCP tools available in Claude Code's context.

Architecture:
- IRemoteFileSystem: Interface (DIP boundary)
- SSHMCPToolsAdapter: Adapter using Claude Code's mcp__ssh-remote__* tools
- No subprocess spawning, no Node.js dependencies
- Works when Project Builder is orchestrated by Claude Code

Usage (when run through Claude Code):
    adapter = SSHMCPToolsAdapter(
        claude_tools=claude_tools_interface,  # Injected by orchestrator
        default_host="root@syd2.jacobhollis.com"
    )
    content = await adapter.read_file(host, path)
"""

import logging
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass

from src.adapters.mcp.ssh_mcp_client import (
    IRemoteFileSystem,
    RemoteFileInfo,
    CommandResult,
    FileType
)

logger = logging.getLogger(__name__)


class SSHMCPToolsAdapter(IRemoteFileSystem):
    """
    Adapter using Claude Code's MCP tools for remote file operations.

    This adapter delegates to mcp__ssh-remote__* tools that are available
    when Claude Code orchestrates Project Builder execution.

    Clean Architecture:
    - Implements IRemoteFileSystem interface (DIP)
    - Depends on abstraction (tool calling interface), not concrete implementation
    - Swap with ParamikoSSHAdapter for standalone execution

    Features:
    - Zero external dependencies (uses Claude's tools)
    - No subprocess spawning
    - Works in any Python environment (venv safe)
    - Simple delegation pattern
    """

    def __init__(
        self,
        tool_caller: Callable[[str, Dict[str, Any]], Any],
        default_host: Optional[str] = None
    ):
        """
        Initialize SSH MCP tools adapter.

        Args:
            tool_caller: Function to call MCP tools (provided by orchestrator)
                         Signature: tool_caller(tool_name, args) -> result
            default_host: Default host for operations (optional)
        """
        self.tool_caller = tool_caller
        self.default_host = default_host

        # Metrics
        self.metrics = {
            "operations": 0,
            "successes": 0,
            "failures": 0,
        }

        logger.info("SSHMCPToolsAdapter initialized (using Claude Code MCP tools)")

    def _get_host(self, host: Optional[str]) -> str:
        """Get host, using default if not specified."""
        if host:
            return host
        if self.default_host:
            return self.default_host
        raise ValueError("No host specified and no default host configured")

    async def read_file(self, host: str, path: str) -> str:
        """Read file content from remote host."""
        self.metrics["operations"] += 1

        try:
            result = self.tool_caller(
                "mcp__ssh-remote__ssh_read_file",
                {"host": self._get_host(host), "path": path}
            )

            self.metrics["successes"] += 1
            logger.debug(f"Read remote file: {host}:{path}")
            return result

        except Exception as e:
            self.metrics["failures"] += 1
            logger.error(f"Failed to read remote file {host}:{path}: {e}")
            raise

    async def write_file(self, host: str, path: str, content: str) -> int:
        """Write content to file on remote host. Returns bytes written."""
        self.metrics["operations"] += 1

        try:
            result = self.tool_caller(
                "mcp__ssh-remote__ssh_write_file",
                {"host": self._get_host(host), "path": path, "content": content}
            )

            bytes_written = len(content.encode('utf-8'))
            self.metrics["successes"] += 1
            logger.debug(f"Wrote remote file: {host}:{path} ({bytes_written} bytes)")
            return bytes_written

        except Exception as e:
            self.metrics["failures"] += 1
            logger.error(f"Failed to write remote file {host}:{path}: {e}")
            raise

    async def list_directory(self, host: str, path: str) -> str:
        """List directory contents on remote host."""
        self.metrics["operations"] += 1

        try:
            result = self.tool_caller(
                "mcp__ssh-remote__ssh_list_dir",
                {"host": self._get_host(host), "path": path}
            )

            self.metrics["successes"] += 1
            logger.debug(f"Listed remote directory: {host}:{path}")
            return result

        except Exception as e:
            self.metrics["failures"] += 1
            logger.error(f"Failed to list remote directory {host}:{path}: {e}")
            raise

    async def glob_files(self, host: str, pattern: str, base_path: str = "/") -> List[str]:
        """Find files matching glob pattern on remote host."""
        self.metrics["operations"] += 1

        try:
            result = self.tool_caller(
                "mcp__ssh-remote__ssh_glob",
                {"host": self._get_host(host), "pattern": pattern, "basePath": base_path}
            )

            # Parse result (format: "Found X files:\n/path1\n/path2\n...")
            if isinstance(result, str):
                lines = result.split('\n')
                if len(lines) > 1:
                    files = [line.strip() for line in lines[1:] if line.strip()]
                else:
                    files = []
            else:
                files = []

            self.metrics["successes"] += 1
            logger.debug(f"Globbed remote files: {host}:{pattern} (found {len(files)})")
            return files

        except Exception as e:
            self.metrics["failures"] += 1
            logger.error(f"Failed to glob remote files {host}:{pattern}: {e}")
            raise

    async def file_exists(self, host: str, path: str) -> RemoteFileInfo:
        """Check if file/directory exists on remote host."""
        self.metrics["operations"] += 1

        try:
            result = self.tool_caller(
                "mcp__ssh-remote__ssh_exists",
                {"host": self._get_host(host), "path": path}
            )

            # Parse result (format: "Path exists (type: file)" or "Path does not exist")
            if isinstance(result, str):
                exists = "exists" in result.lower()
                file_type = None

                if exists:
                    if "file" in result.lower():
                        file_type = FileType.FILE
                    elif "directory" in result.lower():
                        file_type = FileType.DIRECTORY
                    else:
                        file_type = FileType.OTHER
            else:
                exists = False
                file_type = None

            self.metrics["successes"] += 1
            logger.debug(f"Checked remote path: {host}:{path} (exists={exists})")
            return RemoteFileInfo(path=path, exists=exists, file_type=file_type)

        except Exception as e:
            self.metrics["failures"] += 1
            logger.error(f"Failed to check remote path {host}:{path}: {e}")
            raise

    async def execute_command(
        self,
        host: str,
        command: str,
        working_dir: Optional[str] = None
    ) -> CommandResult:
        """Execute command on remote host."""
        self.metrics["operations"] += 1

        try:
            args = {"host": self._get_host(host), "command": command}
            if working_dir:
                args["workingDir"] = working_dir

            result = self.tool_caller(
                "mcp__ssh-remote__ssh_exec",
                args
            )

            # Parse result (format: "Exit Code: X\n\nStdout:\n...\n\nStderr:\n...")
            if isinstance(result, str):
                lines = result.split('\n')
                exit_code = 0
                stdout = ""
                stderr = ""

                current_section = None
                for line in lines:
                    if line.startswith("Exit Code:"):
                        exit_code = int(line.split(":")[1].strip())
                    elif line.startswith("Stdout:"):
                        current_section = "stdout"
                    elif line.startswith("Stderr:"):
                        current_section = "stderr"
                    elif current_section == "stdout":
                        stdout += line + "\n"
                    elif current_section == "stderr":
                        stderr += line + "\n"
            else:
                exit_code = 0
                stdout = str(result)
                stderr = ""

            self.metrics["successes"] += 1
            logger.debug(f"Executed remote command: {host}:{command} (exit={exit_code})")

            return CommandResult(
                stdout=stdout.strip(),
                stderr=stderr.strip(),
                exit_code=exit_code,
                success=(exit_code == 0),
            )

        except Exception as e:
            self.metrics["failures"] += 1
            logger.error(f"Failed to execute remote command {host}:{command}: {e}")
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Get adapter metrics."""
        return {
            "adapter": "SSHMCPToolsAdapter",
            "metrics": self.metrics.copy()
        }


# ============================================================================
# Factory Function
# ============================================================================

def create_ssh_mcp_tools_adapter(
    tool_caller: Callable[[str, Dict[str, Any]], Any],
    default_host: Optional[str] = None
) -> SSHMCPToolsAdapter:
    """
    Factory function to create SSH MCP tools adapter.

    Args:
        tool_caller: Function to call MCP tools (provided by orchestrator)
        default_host: Default host for operations

    Returns:
        Configured SSHMCPToolsAdapter instance
    """
    return SSHMCPToolsAdapter(
        tool_caller=tool_caller,
        default_host=default_host
    )
