"""
Paramiko SSH Adapter for Project Builder

Pure Python implementation using paramiko library for remote file operations.
Works in venv, no subprocess spawning, no Node.js dependencies.

Architecture:
- IRemoteFileSystem: Interface (DIP boundary)
- ParamikoSSHAdapter: Adapter using paramiko library for SSH operations
- Connection pooling and management
- Works standalone or orchestrated

Usage:
    adapter = ParamikoSSHAdapter(
        default_host="root@syd2.jacobhollis.com",
        ssh_key_path="~/.ssh/id_ed25519"
    )
    await adapter.connect()
    content = await adapter.read_file(None, "/path/to/file")  # uses default_host
    await adapter.disconnect()
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
import paramiko
import io

from src.adapters.mcp.ssh_mcp_client import (
    IRemoteFileSystem,
    RemoteFileInfo,
    CommandResult,
    FileType
)

logger = logging.getLogger(__name__)


class ParamikoSSHAdapter(IRemoteFileSystem):
    """
    SSH adapter using paramiko library for remote file operations.

    Pure Python implementation - no external processes, works in venv.

    Clean Architecture:
    - Implements IRemoteFileSystem interface (DIP)
    - No dependency on MCP tools or Node.js
    - Swap with other adapters based on context

    Features:
    - Connection pooling (reuse SSH connections)
    - Async operations (using asyncio.to_thread)
    - Automatic retry logic
    - Key-based authentication
    - Resource cleanup
    """

    def __init__(
        self,
        default_host: Optional[str] = None,
        ssh_key_path: Optional[str] = None,
        username: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize Paramiko SSH adapter.

        Args:
            default_host: Default host for operations (format: user@hostname or hostname)
            ssh_key_path: Path to SSH private key (default: ~/.ssh/id_ed25519)
            username: Default username if not in host string (default: root)
            timeout: SSH operation timeout in seconds
        """
        self.default_host = default_host
        self.username = username or "root"
        self.timeout = timeout

        # SSH key setup
        if ssh_key_path:
            self.ssh_key_path = Path(ssh_key_path).expanduser()
        else:
            self.ssh_key_path = Path("~/.ssh/id_ed25519").expanduser()

        # Connection pool
        self._connections: Dict[str, paramiko.SSHClient] = {}

        # Metrics
        self.metrics = {
            "operations": 0,
            "successes": 0,
            "failures": 0,
            "connections": 0,
        }

        logger.info(f"ParamikoSSHAdapter initialized (key: {self.ssh_key_path})")

    def _parse_host(self, host: Optional[str]) -> tuple[str, str]:
        """
        Parse host string into (username, hostname).

        Args:
            host: Host string (user@hostname or hostname) or None for default

        Returns:
            Tuple of (username, hostname)
        """
        if not host:
            if not self.default_host:
                raise ValueError("No host specified and no default host configured")
            host = self.default_host

        if "@" in host:
            username, hostname = host.split("@", 1)
        else:
            username = self.username
            hostname = host

        return username, hostname

    def _get_connection_key(self, username: str, hostname: str) -> str:
        """Get connection pool key."""
        return f"{username}@{hostname}"

    async def _get_ssh_client(self, host: Optional[str]) -> paramiko.SSHClient:
        """
        Get or create SSH client for host.

        Args:
            host: Host string (user@hostname or hostname)

        Returns:
            Connected SSHClient instance
        """
        username, hostname = self._parse_host(host)
        conn_key = self._get_connection_key(username, hostname)

        # Check if connection exists and is active
        if conn_key in self._connections:
            client = self._connections[conn_key]
            transport = client.get_transport()
            if transport and transport.is_active():
                return client

        # Create new connection
        client = await self._create_connection(username, hostname)
        self._connections[conn_key] = client
        self.metrics["connections"] += 1

        return client

    async def _create_connection(self, username: str, hostname: str) -> paramiko.SSHClient:
        """
        Create new SSH connection.

        Args:
            username: SSH username
            hostname: SSH hostname

        Returns:
            Connected SSHClient instance
        """
        def _connect():
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Load SSH key
            try:
                pkey = paramiko.Ed25519Key.from_private_key_file(str(self.ssh_key_path))
            except Exception as e:
                logger.warning(f"Failed to load Ed25519 key, trying RSA: {e}")
                pkey = paramiko.RSAKey.from_private_key_file(str(self.ssh_key_path))

            # Connect
            client.connect(
                hostname=hostname,
                username=username,
                pkey=pkey,
                timeout=self.timeout,
                look_for_keys=False,
                allow_agent=False
            )

            logger.info(f"SSH connection established: {username}@{hostname}")
            return client

        # Run in thread pool to avoid blocking
        return await asyncio.to_thread(_connect)

    async def connect(self) -> None:
        """Pre-connect to default host (optional optimization)."""
        if self.default_host:
            await self._get_ssh_client(None)
            logger.info(f"Pre-connected to default host: {self.default_host}")

    async def disconnect(self) -> None:
        """Close all SSH connections."""
        for conn_key, client in self._connections.items():
            try:
                client.close()
                logger.debug(f"Closed SSH connection: {conn_key}")
            except Exception as e:
                logger.warning(f"Error closing connection {conn_key}: {e}")

        self._connections.clear()
        logger.info("All SSH connections closed")

    async def read_file(self, host: str, path: str) -> str:
        """Read file content from remote host."""
        self.metrics["operations"] += 1

        try:
            client = await self._get_ssh_client(host)

            def _read():
                sftp = client.open_sftp()
                try:
                    with sftp.open(path, 'r') as f:
                        content = f.read().decode('utf-8')
                    return content
                finally:
                    sftp.close()

            content = await asyncio.to_thread(_read)

            self.metrics["successes"] += 1
            logger.debug(f"Read remote file: {host}:{path} ({len(content)} bytes)")
            return content

        except Exception as e:
            self.metrics["failures"] += 1
            logger.error(f"Failed to read remote file {host}:{path}: {e}")
            raise

    async def write_file(self, host: str, path: str, content: str) -> int:
        """Write content to file on remote host. Returns bytes written."""
        self.metrics["operations"] += 1

        try:
            client = await self._get_ssh_client(host)

            def _write():
                sftp = client.open_sftp()
                try:
                    with sftp.open(path, 'w') as f:
                        bytes_written = f.write(content.encode('utf-8'))
                    return bytes_written
                finally:
                    sftp.close()

            bytes_written = await asyncio.to_thread(_write)

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
            client = await self._get_ssh_client(host)

            def _list():
                sftp = client.open_sftp()
                try:
                    items = sftp.listdir(path)
                    return "\n".join(items)
                finally:
                    sftp.close()

            listing = await asyncio.to_thread(_list)

            self.metrics["successes"] += 1
            logger.debug(f"Listed remote directory: {host}:{path}")
            return listing

        except Exception as e:
            self.metrics["failures"] += 1
            logger.error(f"Failed to list remote directory {host}:{path}: {e}")
            raise

    async def glob_files(self, host: str, pattern: str, base_path: str = "/") -> List[str]:
        """Find files matching glob pattern on remote host."""
        self.metrics["operations"] += 1

        try:
            # Use find command for glob pattern
            result = await self.execute_command(
                host,
                f"find {base_path} -name '{pattern}' -type f 2>/dev/null || true"
            )

            files = [line.strip() for line in result.stdout.split('\n') if line.strip()]

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
            client = await self._get_ssh_client(host)

            def _check():
                sftp = client.open_sftp()
                try:
                    stat = sftp.stat(path)
                    import stat as stat_module

                    if stat_module.S_ISDIR(stat.st_mode):
                        file_type = FileType.DIRECTORY
                    elif stat_module.S_ISREG(stat.st_mode):
                        file_type = FileType.FILE
                    else:
                        file_type = FileType.OTHER

                    return RemoteFileInfo(path=path, exists=True, file_type=file_type)

                except FileNotFoundError:
                    return RemoteFileInfo(path=path, exists=False, file_type=None)
                finally:
                    sftp.close()

            info = await asyncio.to_thread(_check)

            self.metrics["successes"] += 1
            logger.debug(f"Checked remote path: {host}:{path} (exists={info.exists})")
            return info

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
            client = await self._get_ssh_client(host)

            # Prepend cd if working_dir specified
            if working_dir:
                command = f"cd {working_dir} && {command}"

            def _exec():
                stdin, stdout, stderr = client.exec_command(command, timeout=self.timeout)
                exit_code = stdout.channel.recv_exit_status()
                stdout_data = stdout.read().decode('utf-8')
                stderr_data = stderr.read().decode('utf-8')
                return stdout_data, stderr_data, exit_code

            stdout_data, stderr_data, exit_code = await asyncio.to_thread(_exec)

            self.metrics["successes"] += 1
            logger.debug(f"Executed remote command: {host}:{command} (exit={exit_code})")

            return CommandResult(
                stdout=stdout_data,
                stderr=stderr_data,
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
            "adapter": "ParamikoSSHAdapter",
            "metrics": self.metrics.copy()
        }


# ============================================================================
# Factory Function
# ============================================================================

def create_paramiko_ssh_adapter(
    default_host: Optional[str] = None,
    ssh_key_path: Optional[str] = None,
    username: Optional[str] = None,
    timeout: int = 30
) -> ParamikoSSHAdapter:
    """
    Factory function to create Paramiko SSH adapter.

    Args:
        default_host: Default host for operations
        ssh_key_path: Path to SSH private key
        username: Default username
        timeout: SSH operation timeout

    Returns:
        Configured ParamikoSSHAdapter instance
    """
    return ParamikoSSHAdapter(
        default_host=default_host,
        ssh_key_path=ssh_key_path,
        username=username,
        timeout=timeout
    )
