"""ResourceResolver - ensures task file resources are available and persisted.

Coordinates file I/O through the IFileStore port and manages FileSnapshot
entries in the project's world_state.

Responsibilities:
- Pre-load input files declared by tasks into world_state['file_snapshots']
- Write back modified output files from world_state to storage when needed

Notes:
- FileSnapshot objects are stored in world_state under a mapping keyed by the
  FileRef URI (ref.to_uri()).
- This class is async to support I/O-bound backends.
"""

from __future__ import annotations

from typing import Dict, Any

from src.core.entities.file_ref import FileRef
from src.core.entities.file_snapshot import FileSnapshot
from src.core.ports.file_store import IFileStore
from src.entities.task_model.task_model import Task


class ResourceResolver:
    """Resolve and persist file resources for tasks.

    Args:
        file_store: IFileStore implementation for reading/writing files
    """

    def __init__(self, file_store: IFileStore) -> None:
        self._file_store = file_store

    async def ensure_inputs(self, task: Task, world_state: Dict[str, Any]) -> None:
        """Ensure all task input files are loaded into world_state.

        For each FileRef in task.resource_inputs, if no existing snapshot is present
        in world_state['file_snapshots'], read content from the file store and add a
        FileSnapshot entry keyed by the file's URI.

        Args:
            task: Task containing resource_inputs (List[FileRef])
            world_state: Mutable world state dictionary
        """
        if not getattr(task, "resource_inputs", None):
            return

        snapshots: Dict[str, FileSnapshot] = world_state.setdefault("file_snapshots", {})  # type: ignore[assignment]

        for ref in task.resource_inputs:
            if not isinstance(ref, FileRef):
                continue

            uri = ref.to_uri()
            if uri in snapshots:
                continue

            content = await self._file_store.read(ref)
            checksum = FileSnapshot.compute_checksum(content)
            snapshots[uri] = FileSnapshot(ref=ref, content=content, checksum=checksum, dirty=False)

    async def persist_outputs(self, task: Task, world_state: Dict[str, Any]) -> None:
        """Persist modified output files from world_state via the file store.

        For each FileRef in task.resource_outputs, if a corresponding snapshot is
        present in world_state['file_snapshots'] and marked dirty, write the content
        back through the file store and update the snapshot to not dirty.

        Args:
            task: Task containing resource_outputs (List[FileRef])
            world_state: Mutable world state dictionary
        """
        if not getattr(task, "resource_outputs", None):
            return

        snapshots: Dict[str, FileSnapshot] = world_state.get("file_snapshots", {})  # type: ignore[assignment]
        if not snapshots:
            return

        for ref in task.resource_outputs:
            if not isinstance(ref, FileRef):
                continue

            uri = ref.to_uri()
            snap = snapshots.get(uri)
            if not isinstance(snap, FileSnapshot):
                continue

            if snap.dirty:
                # Write the latest content to the backing store
                await self._file_store.write(ref, snap.content)

                # Replace snapshot with a clean version (frozen dataclass)
                clean = FileSnapshot(
                    ref=ref,
                    content=snap.content,
                    checksum=FileSnapshot.compute_checksum(snap.content),
                    dirty=False,
                )
                snapshots[uri] = clean

