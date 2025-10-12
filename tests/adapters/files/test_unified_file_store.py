"""Tests for UnifiedFileStore - routing adapter for IFileStore."""

import pytest
from unittest.mock import AsyncMock, Mock
from src.adapters.files.unified_file_store import UnifiedFileStore
from src.core.entities.file_ref import FileRef


@pytest.fixture
def file_backend():
    """Create a mock backend that supports file:// scheme."""
    backend = Mock()
    backend.supports = Mock(side_effect=lambda ref: ref.scheme == "file")
    return backend


@pytest.fixture
def ssh_backend():
    """Create a mock backend that supports ssh:// scheme."""
    backend = Mock()
    backend.supports = Mock(side_effect=lambda ref: ref.scheme == "ssh")
    return backend


@pytest.fixture
def store(file_backend, ssh_backend):
    """Create UnifiedFileStore with mock backends."""
    return UnifiedFileStore([file_backend, ssh_backend])


class TestBackendRouting:
    """Test backend selection and routing."""

    @pytest.mark.asyncio
    async def test_routes_to_file_backend(self, store, file_backend, ssh_backend):
        """Should route file:// refs to file backend."""
        ref = FileRef(scheme="file", host=None, path="/tmp/test.txt")
        file_backend.read = AsyncMock(return_value="file content")

        result = await store.read(ref)

        assert result == "file content"
        file_backend.read.assert_called_once_with(ref)
        assert not ssh_backend.read.called if hasattr(ssh_backend, "read") else True

    @pytest.mark.asyncio
    async def test_routes_to_ssh_backend(self, store, file_backend, ssh_backend):
        """Should route ssh:// refs to SSH backend."""
        ref = FileRef(scheme="ssh", host="host", path="/opt/test.py")
        ssh_backend.read = AsyncMock(return_value="ssh content")

        result = await store.read(ref)

        assert result == "ssh content"
        ssh_backend.read.assert_called_once_with(ref)
        assert not file_backend.read.called if hasattr(file_backend, "read") else True

    @pytest.mark.asyncio
    async def test_no_backend_supports_ref(self, store):
        """Should raise ValueError when no backend supports ref."""
        ref = FileRef(scheme="s3", host="bucket", path="/key/file.txt")

        with pytest.raises(ValueError) as exc_info:
            await store.read(ref)

        assert "No file backend supports ref" in str(exc_info.value)
        assert "scheme='s3'" in str(exc_info.value)


class TestRead:
    """Test read() method."""

    @pytest.mark.asyncio
    async def test_read_delegates_to_backend(self, store, file_backend):
        """Should delegate read to appropriate backend."""
        ref = FileRef(scheme="file", host=None, path="/tmp/test.txt")
        file_backend.read = AsyncMock(return_value="content")

        result = await store.read(ref)

        assert result == "content"
        file_backend.read.assert_called_once_with(ref)

    @pytest.mark.asyncio
    async def test_read_propagates_file_not_found(self, store, file_backend):
        """Should propagate FileNotFoundError from backend."""
        ref = FileRef(scheme="file", host=None, path="/tmp/nonexistent.txt")
        file_backend.read = AsyncMock(side_effect=FileNotFoundError("File not found"))

        with pytest.raises(FileNotFoundError):
            await store.read(ref)

    @pytest.mark.asyncio
    async def test_read_propagates_permission_error(self, store, file_backend):
        """Should propagate PermissionError from backend."""
        ref = FileRef(scheme="file", host=None, path="/tmp/secret.txt")
        file_backend.read = AsyncMock(side_effect=PermissionError("Access denied"))

        with pytest.raises(PermissionError):
            await store.read(ref)


class TestWrite:
    """Test write() method."""

    @pytest.mark.asyncio
    async def test_write_delegates_to_backend(self, store, file_backend):
        """Should delegate write to appropriate backend."""
        ref = FileRef(scheme="file", host=None, path="/tmp/test.txt")
        file_backend.write = AsyncMock()

        await store.write(ref, "new content")

        file_backend.write.assert_called_once_with(ref, "new content")

    @pytest.mark.asyncio
    async def test_write_propagates_permission_error(self, store, file_backend):
        """Should propagate PermissionError from backend."""
        ref = FileRef(scheme="file", host=None, path="/tmp/readonly.txt")
        file_backend.write = AsyncMock(side_effect=PermissionError("Write denied"))

        with pytest.raises(PermissionError):
            await store.write(ref, "content")

    @pytest.mark.asyncio
    async def test_write_propagates_io_error(self, store, file_backend):
        """Should propagate IOError from backend."""
        ref = FileRef(scheme="file", host=None, path="/tmp/test.txt")
        file_backend.write = AsyncMock(side_effect=IOError("Disk full"))

        with pytest.raises(IOError):
            await store.write(ref, "content")


class TestExists:
    """Test exists() method."""

    @pytest.mark.asyncio
    async def test_exists_delegates_to_backend(self, store, file_backend):
        """Should delegate exists to appropriate backend."""
        ref = FileRef(scheme="file", host=None, path="/tmp/test.txt")
        file_backend.exists = AsyncMock(return_value=True)

        result = await store.exists(ref)

        assert result is True
        file_backend.exists.assert_called_once_with(ref)

    @pytest.mark.asyncio
    async def test_exists_returns_false(self, store, file_backend):
        """Should return False when backend returns False."""
        ref = FileRef(scheme="file", host=None, path="/tmp/nonexistent.txt")
        file_backend.exists = AsyncMock(return_value=False)

        result = await store.exists(ref)

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_propagates_permission_error(self, store, file_backend):
        """Should propagate PermissionError from backend."""
        ref = FileRef(scheme="file", host=None, path="/tmp/secret.txt")
        file_backend.exists = AsyncMock(side_effect=PermissionError("Access denied"))

        with pytest.raises(PermissionError):
            await store.exists(ref)


class TestListDir:
    """Test list_dir() method."""

    @pytest.mark.asyncio
    async def test_list_dir_delegates_to_backend(self, store, file_backend):
        """Should delegate list_dir to appropriate backend."""
        ref = FileRef(scheme="file", host=None, path="/tmp/dir")
        expected_refs = [
            FileRef(scheme="file", host=None, path="/tmp/dir/file1.txt"),
            FileRef(scheme="file", host=None, path="/tmp/dir/file2.txt"),
        ]
        file_backend.list_dir = AsyncMock(return_value=expected_refs)

        results = await store.list_dir(ref)

        assert results == expected_refs
        file_backend.list_dir.assert_called_once_with(ref)

    @pytest.mark.asyncio
    async def test_list_dir_propagates_file_not_found(self, store, file_backend):
        """Should propagate FileNotFoundError from backend."""
        ref = FileRef(scheme="file", host=None, path="/tmp/nonexistent")
        file_backend.list_dir = AsyncMock(side_effect=FileNotFoundError("Not found"))

        with pytest.raises(FileNotFoundError):
            await store.list_dir(ref)

    @pytest.mark.asyncio
    async def test_list_dir_propagates_not_a_directory(self, store, file_backend):
        """Should propagate NotADirectoryError from backend."""
        ref = FileRef(scheme="file", host=None, path="/tmp/file.txt")
        file_backend.list_dir = AsyncMock(side_effect=NotADirectoryError("Not a dir"))

        with pytest.raises(NotADirectoryError):
            await store.list_dir(ref)


class TestMultipleBackends:
    """Test behavior with multiple backends."""

    @pytest.mark.asyncio
    async def test_uses_first_matching_backend(self):
        """Should use first backend that supports ref when multiple match."""
        # Create two backends that both claim to support file://
        backend1 = Mock()
        backend1.supports = Mock(return_value=True)
        backend1.read = AsyncMock(return_value="backend1")

        backend2 = Mock()
        backend2.supports = Mock(return_value=True)
        backend2.read = AsyncMock(return_value="backend2")

        store = UnifiedFileStore([backend1, backend2])
        ref = FileRef(scheme="file", host=None, path="/tmp/test.txt")

        result = await store.read(ref)

        # Should use backend1 (first in list)
        assert result == "backend1"
        backend1.read.assert_called_once()
        assert not backend2.read.called

    @pytest.mark.asyncio
    async def test_empty_backend_list(self):
        """Should raise ValueError when no backends registered."""
        store = UnifiedFileStore([])
        ref = FileRef(scheme="file", host=None, path="/tmp/test.txt")

        with pytest.raises(ValueError) as exc_info:
            await store.read(ref)

        assert "No file backend supports ref" in str(exc_info.value)
