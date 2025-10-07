"""
SSH MCP Client Adapter for Project Builder

Provides Python interface to SSH MCP server for remote codebase access.
Follows Clean Architecture principles with proper abstraction layers.

Architecture:
- IRemoteFileSystem: Interface for remote file operations (DIP)
- SSHMCPClient: Adapter implementing IRemoteFileSystem via MCP protocol
- Connection management and error handling
- Retry logic with exponential backoff

Usage:
    client = SSHMCPClient(server_path="/path/to/ssh-mcp-server.js")
    await client.connect()

    content = await client.read_file("root@syd2.jacobhollis.com", "/opt/project/file.py")
    await client.write_file("root@syd2.jacobhollis.com", "/opt/project/new.py", "content")

    await client.disconnect()
"""

import asyncio
import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================================
# Domain Entities
# ============================================================================

class FileType(Enum):
    """File type enumeration."""
    FILE = "file"
    DIRECTORY = "directory"
    OTHER = "other"


@dataclass
class RemoteFileInfo:
    """Information about a remote file or directory."""
    path: str
    exists: bool
    file_type: Optional[FileType] = None


@dataclass
class CommandResult:
    """Result of remote command execution."""
    stdout: str
    stderr: str
    exit_code: int
    success: bool


# ============================================================================
# Interfaces (Clean Architecture - DIP)
# ============================================================================

class IRemoteFileSystem(ABC):
    """
    Interface for remote file system operations.

    Follows Dependency Inversion Principle - high-level modules depend on this
    abstraction, not concrete implementations.
    """

    @abstractmethod
    async def read_file(self, host: str, path: str) -> str:
        """Read file content from remote host."""
        pass

    @abstractmethod
    async def write_file(self, host: str, path: str, content: str) -> int:
        """Write content to file on remote host. Returns bytes written."""
        pass

    @abstractmethod
    async def list_directory(self, host: str, path: str) -> str:
        """List directory contents on remote host."""
        pass

    @abstractmethod
    async def glob_files(self, host: str, pattern: str, base_path: str = "/") -> List[str]:
        """Find files matching glob pattern on remote host."""
        pass

    @abstractmethod
    async def file_exists(self, host: str, path: str) -> RemoteFileInfo:
        """Check if file/directory exists on remote host."""
        pass

    @abstractmethod
    async def execute_command(
        self,
        host: str,
        command: str,
        working_dir: Optional[str] = None
    ) -> CommandResult:
        """Execute command on remote host."""
        pass


# ============================================================================
# MCP Client Implementation
# ============================================================================

class SSHMCPClient(IRemoteFileSystem):
    """
    SSH MCP client adapter for remote file operations.

    Implements IRemoteFileSystem using MCP protocol to communicate with
    ssh-mcp-server.js Node.js server.

    Features:
    - Async subprocess communication via stdio
    - Automatic retry with exponential backoff
    - Connection pooling (handled by MCP server)
    - Comprehensive error handling
    - Metrics collection
    """

    def __init__(
        self,
        server_path: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 60.0,
    ):
        """
        Initialize SSH MCP client.

        Args:
            server_path: Path to ssh-mcp-server.js executable
            max_retries: Maximum number of retry attempts
            retry_delay: Initial retry delay in seconds (exponential backoff)
            timeout: Operation timeout in seconds
        """
        self.server_path = server_path
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

        self._process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._connected = False

        # Metrics
        self.metrics = {
            "operations": 0,
            "successes": 0,
            "failures": 0,
            "retries": 0,
        }

    async def connect(self) -> None:
        """Start MCP server process and establish connection."""
        if self._connected:
            logger.warning("Already connected to SSH MCP server")
            return

        try:
            logger.info(f"Starting SSH MCP server: {self.server_path}")

            self._process = await asyncio.create_subprocess_exec(
                "node",
                self.server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            self._connected = True
            logger.info("SSH MCP server connected")

            # Start stderr reader for logging
            asyncio.create_task(self._read_stderr())

        except Exception as e:
            logger.error(f"Failed to start SSH MCP server: {e}")
            raise

    async def disconnect(self) -> None:
        """Stop MCP server process and cleanup."""
        if not self._connected:
            return

        try:
            logger.info("Disconnecting from SSH MCP server")

            if self._process:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)

            self._connected = False
            logger.info("SSH MCP server disconnected")

        except asyncio.TimeoutError:
            logger.warning("SSH MCP server did not terminate gracefully, killing")
            if self._process:
                self._process.kill()
                await self._process.wait()
        except Exception as e:
            logger.error(f"Error disconnecting from SSH MCP server: {e}")

    async def _read_stderr(self) -> None:
        """Read and log stderr from MCP server."""
        if not self._process or not self._process.stderr:
            return

        try:
            async for line in self._process.stderr:
                logger.debug(f"SSH MCP Server: {line.decode().strip()}")
        except Exception as e:
            logger.error(f"Error reading stderr: {e}")

    async def _call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call MCP tool with retry logic.

        Args:
            tool_name: Name of the MCP tool to call
            arguments: Tool arguments

        Returns:
            Tool response as dictionary

        Raises:
            RuntimeError: If not connected or operation fails after retries
        """
        if not self._connected or not self._process:
            raise RuntimeError("Not connected to SSH MCP server")

        self.metrics["operations"] += 1

        for attempt in range(self.max_retries):
            try:
                # Build MCP request
                self._request_id += 1
                request = {
                    "jsonrpc": "2.0",
                    "id": self._request_id,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments,
                    },
                }

                # Send request
                request_json = json.dumps(request) + "\n"
                self._process.stdin.write(request_json.encode())
                await self._process.stdin.drain()

                # Read response with timeout
                response_line = await asyncio.wait_for(
                    self._process.stdout.readline(),
                    timeout=self.timeout,
                )

                response = json.loads(response_line.decode())

                # Check for errors
                if "error" in response:
                    error_msg = response["error"].get("message", "Unknown error")
                    raise RuntimeError(f"MCP error: {error_msg}")

                # Extract result
                result = response.get("result", {})

                # Check if tool returned error
                if result.get("isError"):
                    content = result.get("content", [{}])[0].get("text", "Unknown error")
                    raise RuntimeError(f"Tool error: {content}")

                self.metrics["successes"] += 1
                return result

            except asyncio.TimeoutError:
                logger.warning(f"Timeout calling {tool_name} (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    self.metrics["retries"] += 1
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                else:
                    self.metrics["failures"] += 1
                    raise RuntimeError(f"Timeout calling {tool_name} after {self.max_retries} attempts")

            except Exception as e:
                logger.error(f"Error calling {tool_name}: {e} (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    self.metrics["retries"] += 1
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))
                else:
                    self.metrics["failures"] += 1
                    raise

    # ========================================================================
    # IRemoteFileSystem Implementation
    # ========================================================================

    async def list_directory(self, host: str, path: str) -> str:
        """List directory contents on remote host."""
        result = await self._call_tool("ssh_list_dir", {"host": host, "path": path})
        listing = result.get("content", [{}])[0].get("text", "")
        return listing

    async def glob_files(self, host: str, pattern: str, base_path: str = "/") -> List[str]:
        """Find files matching glob pattern on remote host."""
        result = await self._call_tool(
            "ssh_glob",
            {"host": host, "pattern": pattern, "basePath": base_path}
        )
        response_text = result.get("content", [{}])[0].get("text", "")

        # Parse "Found X files:\n/path1\n/path2\n..."
        lines = response_text.split('\n')
        if len(lines) > 1:
            return [line.strip() for line in lines[1:] if line.strip()]
        return []

    async def file_exists(self, host: str, path: str) -> RemoteFileInfo:
        """Check if file/directory exists on remote host."""
        result = await self._call_tool("ssh_exists", {"host": host, "path": path})
        response_text = result.get("content", [{}])[0].get("text", "")

        # Parse "Path exists (type: file)" or "Path does not exist"
        exists = "exists" in response_text.lower()
        file_type = None

        if exists:
            if "file" in response_text:
                file_type = FileType.FILE
            elif "directory" in response_text:
                file_type = FileType.DIRECTORY
            else:
                file_type = FileType.OTHER

        return RemoteFileInfo(path=path, exists=exists, file_type=file_type)

    async def execute_command(
        self,
        host: str,
        command: str,
        working_dir: Optional[str] = None
    ) -> CommandResult:
        """Execute command on remote host."""
        args = {"host": host, "command": command}
        if working_dir:
            args["workingDir"] = working_dir

        result = await self._call_tool("ssh_exec", args)
        response_text = result.get("content", [{}])[0].get("text", "")

        # Parse "Exit Code: X\n\nStdout:\n...\n\nStderr:\n..."
        lines = response_text.split('\n')
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

        return CommandResult(
            stdout=stdout.strip(),
            stderr=stderr.strip(),
            exit_code=exit_code,
            success=(exit_code == 0),
        )

    async def get_metrics(self) -> Dict[str, Any]:
        """Get metrics from both client and server."""
        # Get server metrics
        server_metrics = {}
        try:
            result = await self._call_tool("ssh_get_metrics", {})
            metrics_text = result.get("content", [{}])[0].get("text", "{}")
            server_metrics = json.loads(metrics_text)
        except Exception as e:
            logger.warning(f"Failed to get server metrics: {e}")

        return {
            "client": self.metrics,
            "server": server_metrics,
        }


# ============================================================================
# Context Manager Support
# ============================================================================

class SSHMCPClientContext:
    """Context manager for SSHMCPClient to ensure proper cleanup."""

    def __init__(self, client: SSHMCPClient):
        self.client = client

    async def __aenter__(self) -> SSHMCPClient:
        await self.client.connect()
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.disconnect()
        return False


# ============================================================================
# Factory Function
# ============================================================================

def create_ssh_mcp_client(
    server_path: str = "/home/ui-cli_jake/unified-intelligence-cli/ssh-mcp-server.js",
    **kwargs
) -> SSHMCPClient:
    """
    Factory function to create SSH MCP client.

    Args:
        server_path: Path to ssh-mcp-server.js
        **kwargs: Additional arguments for SSHMCPClient

    Returns:
        Configured SSHMCPClient instance
    """
    return SSHMCPClient(server_path=server_path, **kwargs)

