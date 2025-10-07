"""Tests for ResourceResolver - file resource management."""

import pytest
from unittest.mock import AsyncMock, Mock
from src.project_builder.execution.resource_resolver import ResourceResolver
from src.core.entities.file_ref import FileRef
from src.core.entities.file_snapshot import FileSnapshot
from src.entities.task_model.task_model import Task


@pytest.fixture
def mock_file_store():
    """Create a mock IFileStore."""
    return Mock()


@pytest.fixture
def resolver(mock_file_store):
    """Create ResourceResolver with mock file store."""
    return ResourceResolver(mock_file_store)


@pytest.fixture
def sample_task():
    """Create a sample task with resource inputs/outputs."""
    task = Task()
    task.resource_inputs = [
        FileRef(scheme="file", host=None, path="/tmp/input1.txt"),
        FileRef(scheme="file", host=None, path="/tmp/input2.txt"),
    ]
    task.resource_outputs = [
        FileRef(scheme="file", host=None, path="/tmp/output.txt"),
    ]
    return task


class TestEnsureInputs:
    """Test ensure_inputs() method."""

    @pytest.mark.asyncio
    async def test_loads_missing_inputs(self, resolver, mock_file_store):
        """Should load missing input files into world_state."""
        task = Task()
        task.resource_inputs = [
            FileRef(scheme="file", host=None, path="/tmp/file1.txt"),
            FileRef(scheme="file", host=None, path="/tmp/file2.txt"),
        ]
        world_state = {}

        mock_file_store.read = AsyncMock(side_effect=["content1", "content2"])

        await resolver.ensure_inputs(task, world_state)

        assert "file_snapshots" in world_state
        snapshots = world_state["file_snapshots"]
        assert len(snapshots) == 2
        assert "file:///tmp/file1.txt" in snapshots
        assert "file:///tmp/file2.txt" in snapshots
        assert snapshots["file:///tmp/file1.txt"].content == "content1"
        assert snapshots["file:///tmp/file2.txt"].content == "content2"
        assert snapshots["file:///tmp/file1.txt"].dirty is False
        assert snapshots["file:///tmp/file2.txt"].dirty is False

    @pytest.mark.asyncio
    async def test_skips_existing_snapshots(self, resolver, mock_file_store):
        """Should skip files already in world_state."""
        ref1 = FileRef(scheme="file", host=None, path="/tmp/file1.txt")
        ref2 = FileRef(scheme="file", host=None, path="/tmp/file2.txt")

        existing_snapshot = FileSnapshot(
            ref=ref1,
            content="existing content",
            checksum=FileSnapshot.compute_checksum("existing content"),
            dirty=False
        )

        world_state = {
            "file_snapshots": {
                ref1.to_uri(): existing_snapshot
            }
        }

        task = Task()
        task.resource_inputs = [ref1, ref2]

        mock_file_store.read = AsyncMock(return_value="new content")

        await resolver.ensure_inputs(task, world_state)

        snapshots = world_state["file_snapshots"]
        # ref1 should still have existing content
        assert snapshots[ref1.to_uri()].content == "existing content"
        # ref2 should be loaded
        assert snapshots[ref2.to_uri()].content == "new content"
        # read should only be called once (for ref2)
        assert mock_file_store.read.call_count == 1

    @pytest.mark.asyncio
    async def test_handles_empty_inputs(self, resolver, mock_file_store):
        """Should handle task with no resource_inputs."""
        task = Task()
        task.resource_inputs = []
        world_state = {}

        await resolver.ensure_inputs(task, world_state)

        # Should not fail, may create empty file_snapshots dict
        assert mock_file_store.read.call_count == 0

    @pytest.mark.asyncio
    async def test_propagates_file_not_found(self, resolver, mock_file_store):
        """Should propagate FileNotFoundError from file_store."""
        task = Task()
        task.resource_inputs = [FileRef(scheme="file", host=None, path="/tmp/nonexistent.txt")]
        world_state = {}

        mock_file_store.read = AsyncMock(side_effect=FileNotFoundError("File not found"))

        with pytest.raises(FileNotFoundError):
            await resolver.ensure_inputs(task, world_state)


class TestPersistOutputs:
    """Test persist_outputs() method."""

    @pytest.mark.asyncio
    async def test_persists_dirty_outputs(self, resolver, mock_file_store):
        """Should write dirty output files to file_store."""
        ref = FileRef(scheme="file", host=None, path="/tmp/output.txt")
        dirty_snapshot = FileSnapshot(
            ref=ref,
            content="modified content",
            checksum=FileSnapshot.compute_checksum("modified content"),
            dirty=True
        )

        world_state = {
            "file_snapshots": {
                ref.to_uri(): dirty_snapshot
            }
        }

        task = Task()
        task.resource_outputs = [ref]

        mock_file_store.write = AsyncMock()

        await resolver.persist_outputs(task, world_state)

        # Should write to file_store
        mock_file_store.write.assert_called_once_with(ref, "modified content")

        # Should mark snapshot as clean
        snapshot = world_state["file_snapshots"][ref.to_uri()]
        assert snapshot.dirty is False

    @pytest.mark.asyncio
    async def test_skips_clean_outputs(self, resolver, mock_file_store):
        """Should skip writing clean (non-dirty) outputs."""
        ref = FileRef(scheme="file", host=None, path="/tmp/output.txt")
        clean_snapshot = FileSnapshot(
            ref=ref,
            content="unchanged content",
            checksum=FileSnapshot.compute_checksum("unchanged content"),
            dirty=False
        )

        world_state = {
            "file_snapshots": {
                ref.to_uri(): clean_snapshot
            }
        }

        task = Task()
        task.resource_outputs = [ref]

        mock_file_store.write = AsyncMock()

        await resolver.persist_outputs(task, world_state)

        # Should not write to file_store
        assert mock_file_store.write.call_count == 0

    @pytest.mark.asyncio
    async def test_handles_missing_snapshot(self, resolver, mock_file_store):
        """Should handle output ref not in world_state gracefully."""
        ref = FileRef(scheme="file", host=None, path="/tmp/output.txt")
        world_state = {"file_snapshots": {}}

        task = Task()
        task.resource_outputs = [ref]

        mock_file_store.write = AsyncMock()

        # Should not fail
        await resolver.persist_outputs(task, world_state)

        # Should not attempt to write
        assert mock_file_store.write.call_count == 0

    @pytest.mark.asyncio
    async def test_handles_empty_outputs(self, resolver, mock_file_store):
        """Should handle task with no resource_outputs."""
        task = Task()
        task.resource_outputs = []
        world_state = {}

        mock_file_store.write = AsyncMock()

        await resolver.persist_outputs(task, world_state)

        assert mock_file_store.write.call_count == 0

    @pytest.mark.asyncio
    async def test_handles_empty_world_state(self, resolver, mock_file_store):
        """Should handle world_state with no file_snapshots."""
        ref = FileRef(scheme="file", host=None, path="/tmp/output.txt")
        task = Task()
        task.resource_outputs = [ref]
        world_state = {}

        mock_file_store.write = AsyncMock()

        await resolver.persist_outputs(task, world_state)

        assert mock_file_store.write.call_count == 0

    @pytest.mark.asyncio
    async def test_persists_multiple_dirty_outputs(self, resolver, mock_file_store):
        """Should persist multiple dirty outputs."""
        ref1 = FileRef(scheme="file", host=None, path="/tmp/output1.txt")
        ref2 = FileRef(scheme="file", host=None, path="/tmp/output2.txt")

        world_state = {
            "file_snapshots": {
                ref1.to_uri(): FileSnapshot(ref=ref1, content="content1",
                                            checksum=FileSnapshot.compute_checksum("content1"), dirty=True),
                ref2.to_uri(): FileSnapshot(ref=ref2, content="content2",
                                            checksum=FileSnapshot.compute_checksum("content2"), dirty=True),
            }
        }

        task = Task()
        task.resource_outputs = [ref1, ref2]

        mock_file_store.write = AsyncMock()

        await resolver.persist_outputs(task, world_state)

        # Should write both files
        assert mock_file_store.write.call_count == 2

        # Both should be clean now
        assert world_state["file_snapshots"][ref1.to_uri()].dirty is False
        assert world_state["file_snapshots"][ref2.to_uri()].dirty is False


class TestIntegration:
    """Integration tests for ResourceResolver."""

    @pytest.mark.asyncio
    async def test_roundtrip_input_modify_persist(self, resolver, mock_file_store):
        """Test full roundtrip: load input, modify, persist output."""
        ref = FileRef(scheme="file", host=None, path="/tmp/file.txt")

        task = Task()
        task.resource_inputs = [ref]
        task.resource_outputs = [ref]

        world_state = {}

        # Setup mock to return original content
        mock_file_store.read = AsyncMock(return_value="original content")
        mock_file_store.write = AsyncMock()

        # Step 1: Ensure inputs (loads file)
        await resolver.ensure_inputs(task, world_state)

        snapshot = world_state["file_snapshots"][ref.to_uri()]
        assert snapshot.content == "original content"
        assert snapshot.dirty is False

        # Step 2: Simulate modification
        modified_snapshot = snapshot.with_content("modified content")
        world_state["file_snapshots"][ref.to_uri()] = modified_snapshot
        assert modified_snapshot.dirty is True

        # Step 3: Persist outputs (writes modified content)
        await resolver.persist_outputs(task, world_state)

        mock_file_store.write.assert_called_once_with(ref, "modified content")

        # Snapshot should be clean after persist
        final_snapshot = world_state["file_snapshots"][ref.to_uri()]
        assert final_snapshot.dirty is False
        assert final_snapshot.content == "modified content"
