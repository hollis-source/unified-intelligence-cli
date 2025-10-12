"""MCP (Model Context Protocol) adapters for remote operations."""

from .ssh_mcp_client import (
    SSHMCPClient,
    IRemoteFileSystem,
    RemoteFileInfo,
    CommandResult,
    FileType,
    SSHMCPClientContext,
    create_ssh_mcp_client,
)

__all__ = [
    "SSHMCPClient",
    "IRemoteFileSystem",
    "RemoteFileInfo",
    "CommandResult",
    "FileType",
    "SSHMCPClientContext",
    "create_ssh_mcp_client",
]

