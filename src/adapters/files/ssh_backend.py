"""SSHBackend - IFileBackend implementation wrapping ParamikoSSHAdapter.

Infrastructure adapter that provides ssh:// file operations via ParamikoSSHAdapter.
"""
from __future__ import annotations

from typing import List
import posixpath

from src.adapters.files.backend import IFileBackend
from src.core.entities.file_ref import FileRef
from src.adapters.mcp.paramiko_ssh_adapter import ParamikoSSHAdapter
from src.adapters.mcp.ssh_mcp_client import FileType


class SSHBackend(IFileBackend):
    """SSH file backend using ParamikoSSHAdapter for remote operations."""

    def __init__(self, adapter: ParamikoSSHAdapter) -> None:
        self._adapter = adapter

    def supports(self, ref: FileRef) -> bool:
        return ref.scheme == "ssh"

    async def read(self, ref: FileRef) -> str:
        try:
            return await self._adapter.read_file(ref.host or "", ref.path)
        except FileNotFoundError:
            raise
        except PermissionError:
            raise
        except Exception as e:  # Normalize to IOError for unknown I/O errors
            self._raise_ioerror(e, f"Failed to read file {ref}")

    async def write(self, ref: FileRef, content: str) -> None:
        try:
            await self._adapter.write_file(ref.host or "", ref.path, content)
        except PermissionError:
            raise
        except FileNotFoundError:
            # Writing to non-existent directory, normalize as FileNotFoundError
            raise
        except Exception as e:
            self._raise_ioerror(e, f"Failed to write file {ref}")

    async def exists(self, ref: FileRef) -> bool:
        try:
            info = await self._adapter.file_exists(ref.host or "", ref.path)
            return bool(getattr(info, "exists", False))
        except PermissionError:
            raise
        except Exception as e:
            self._raise_ioerror(e, f"Failed to check existence of {ref}")

    async def list_dir(self, ref: FileRef) -> List[FileRef]:
        # Validate the path is a directory first for clearer errors
        try:
            info = await self._adapter.file_exists(ref.host or "", ref.path)
        except Exception as e:
            self._raise_ioerror(e, f"Failed to check directory {ref}")

        if not getattr(info, "exists", False):
            raise FileNotFoundError(f"Directory not found: {ref}")
        if getattr(info, "file_type", None) == FileType.FILE:
            raise NotADirectoryError(f"Not a directory: {ref}")

        try:
            listing = await self._adapter.list_directory(ref.host or "", ref.path)
            names = [line.strip() for line in listing.split("\n") if line.strip()]
            return [
                FileRef(
                    scheme="ssh",
                    host=ref.host,
                    path=posixpath.join(ref.path, name),
                )
                for name in names
            ]
        except FileNotFoundError:
            raise
        except PermissionError:
            raise
        except Exception as e:
            self._raise_ioerror(e, f"Failed to list directory {ref}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _raise_ioerror(exc: Exception, context: str) -> None:
        msg = str(exc).lower()
        if "no such file" in msg or "not found" in msg or "does not exist" in msg:
            raise FileNotFoundError(context) from exc
        if "permission" in msg or "denied" in msg:
            raise PermissionError(context) from exc
        if "not a directory" in msg:
            raise NotADirectoryError(context) from exc
        # Fallback
        raise IOError(f"{context}: {exc}") from exc

