#!/usr/bin/env python3
"""Simple integration test for FileStore architecture.

Tests the complete flow:
1. Create UnifiedFileStore with LocalBackend
2. Create ResourceResolver
3. Simulate task with resource_inputs/outputs
4. Verify files are loaded and persisted
"""

import asyncio
import tempfile
from pathlib import Path

from src.core.entities.file_ref import FileRef
from src.core.entities.file_snapshot import FileSnapshot
from src.adapters.files import LocalBackend, UnifiedFileStore
from src.project_builder.execution.resource_resolver import ResourceResolver
from src.entities.task_model.task_model import Task


async def main():
    print("=== FileStore Integration Test ===\n")

    # Setup: Create temp files
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create input file
        input_file = tmpdir / "input.txt"
        input_file.write_text("Original content")

        # Create output file path (doesn't exist yet)
        output_file = tmpdir / "output.txt"

        print(f"Test directory: {tmpdir}")
        print(f"Input file: {input_file}")
        print(f"Output file: {output_file}\n")

        # Step 1: Create FileStore
        print("1. Creating UnifiedFileStore with LocalBackend...")
        backend = LocalBackend()
        file_store = UnifiedFileStore([backend])
        print("   ✓ FileStore created\n")

        # Step 2: Create ResourceResolver
        print("2. Creating ResourceResolver...")
        resolver = ResourceResolver(file_store)
        print("   ✓ ResourceResolver created\n")

        # Step 3: Create Task with FileRefs
        print("3. Creating Task with resource_inputs and resource_outputs...")
        task = Task()
        task.resource_inputs = [FileRef(scheme="file", host=None, path=str(input_file))]
        task.resource_outputs = [FileRef(scheme="file", host=None, path=str(output_file))]
        print(f"   Inputs: {[ref.to_uri() for ref in task.resource_inputs]}")
        print(f"   Outputs: {[ref.to_uri() for ref in task.resource_outputs]}")
        print("   ✓ Task created\n")

        # Step 4: Test ensure_inputs
        print("4. Testing ensure_inputs (loads files into world_state)...")
        world_state = {}
        await resolver.ensure_inputs(task, world_state)

        assert "file_snapshots" in world_state
        snapshots = world_state["file_snapshots"]
        input_uri = task.resource_inputs[0].to_uri()
        assert input_uri in snapshots
        snapshot = snapshots[input_uri]
        assert snapshot.content == "Original content"
        assert snapshot.dirty is False
        print(f"   ✓ Loaded input file: {snapshot.content!r}")
        print(f"   ✓ Snapshot is clean (dirty={snapshot.dirty})\n")

        # Step 5: Simulate modification
        print("5. Simulating task modification (modifies content in world_state)...")
        output_ref = task.resource_outputs[0]
        modified_snapshot = FileSnapshot(
            ref=output_ref,
            content="Modified content by task",
            checksum=FileSnapshot.compute_checksum("Modified content by task"),
            dirty=True
        )
        world_state["file_snapshots"][output_ref.to_uri()] = modified_snapshot
        print(f"   ✓ Modified content: {modified_snapshot.content!r}")
        print(f"   ✓ Snapshot is dirty (dirty={modified_snapshot.dirty})\n")

        # Step 6: Test persist_outputs
        print("6. Testing persist_outputs (writes dirty snapshots to disk)...")
        await resolver.persist_outputs(task, world_state)

        # Verify file was written
        assert output_file.exists()
        actual_content = output_file.read_text()
        assert actual_content == "Modified content by task"
        print(f"   ✓ File written to disk: {output_file}")
        print(f"   ✓ Content verified: {actual_content!r}")

        # Verify snapshot is now clean
        final_snapshot = world_state["file_snapshots"][output_ref.to_uri()]
        assert final_snapshot.dirty is False
        print(f"   ✓ Snapshot is clean after persist (dirty={final_snapshot.dirty})\n")

        print("=== All Tests Passed ✓ ===")
        print("\nSummary:")
        print("- UnifiedFileStore correctly routes to LocalBackend")
        print("- ResourceResolver loads input files into world_state")
        print("- ResourceResolver persists dirty output files")
        print("- Snapshots track dirty state correctly")
        print("\nFileStore architecture is working end-to-end! 🎉")


if __name__ == "__main__":
    asyncio.run(main())
