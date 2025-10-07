"""LocalBackend - Local filesystem implementation of IFileBackend.

Infrastructure adapter that handles file:// URIs using pathlib.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List

from src.adapters.files.backend import IFileBackend
from src.core.entities.file_ref import FileRef


class LocalBackend(IFileBackend):
    """Local filesystem backend.

    Supports FileRef with scheme == "file". Uses asyncio.to_thread to offload
    blocking filesystem operations to a thread to keep the event loop responsive.
    """

    def supports(self, ref: FileRef) -> bool:
        return ref.scheme == "file"

    async def read(self, ref: FileRef) -> str:
        path = Path(ref.path)

        def _read() -> str:
            try:
                return path.read_text(encoding="utf-8")
            except FileNotFoundError:
                raise
            except PermissionError:
                raise
            except OSError as e:
                # Normalize other OS errors under IOError as per interface contract
                raise IOError(str(e))

        return await asyncio.to_thread(_read)

    async def write(self, ref: FileRef, content: str) -> None:
        path = Path(ref.path)

        def _write() -> None:
            try:
                # Ensure parent directories exist
                parent = path.parent
                if parent:
                    parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            except PermissionError:
                raise
            except FileNotFoundError:
                # Can occur if a component in the path isn't found after checks
                raise
            except OSError as e:
                # Normalize other OS errors under IOError
                raise IOError(str(e))

        await asyncio.to_thread(_write)

    async def exists(self, ref: FileRef) -> bool:
        path = Path(ref.path)

        def _exists() -> bool:
            try:
                return path.exists()
            except PermissionError:
                raise
            except OSError as e:
                # Normalize unexpected OS errors
                raise IOError(str(e))

        return await asyncio.to_thread(_exists)

    async def list_dir(self, ref: FileRef) -> List[FileRef]:
        path = Path(ref.path)

        def _iterdir_paths() -> List[Path]:
            try:
                return list(path.iterdir())
            except FileNotFoundError:
                raise
            except NotADirectoryError:
                raise
            except PermissionError:
                raise
            except OSError as e:
                raise IOError(str(e))

        children = await asyncio.to_thread(_iterdir_paths)

        # Convert to FileRef objects (file scheme has no host)
        return [FileRef(scheme="file", host=None, path=str(child.resolve())) for child in children]

