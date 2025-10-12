"""Tests for SSHBackend - SSH filesystem adapter."""

import pytest
from unittest.mock import AsyncMock, Mock
from src.adapters.files.ssh_backend import SSHBackend
from src.core.entities.file_ref import FileRef
from src.adapters.mcp.ssh_mcp_client import FileType


@pytest.fixture
def mock_adapter():
    """Create a mock ParamikoSSHAdapter."""
    return Mock()


@pytest.fixture
def backend(mock_adapter):
    """Create SSHBackend with mock adapter."""
    return SSHBackend(mock_adapter)


class TestSupports:
    """Test supports() method."""

    @pytest.mark.asyncio
    async def test_supports_ssh_scheme(self, backend):
        """Should support ssh:// scheme."""
        ref = FileRef(scheme="ssh", host="host", path="/opt/file.py")
        assert backend.supports(ref) is True

    @pytest.mark.asyncio
    async def test_rejects_file_scheme(self, backend):
        """Should reject file:// scheme."""
        ref = FileRef(scheme="file", host=None, path="/tmp/test.txt")
        assert backend.supports(ref) is False

    @pytest.mark.asyncio
    async def test_rejects_s3_scheme(self, backend):
        """Should reject s3:// scheme."""
        ref = FileRef(scheme="s3", host="bucket", path="/key/file.txt")
        assert backend.supports(ref) is False


class TestRead:
    """Test read() method."""

    @pytest.mark.asyncio
    async def test_read_file(self, backend, mock_adapter):
        """Should read file content via adapter."""
        ref = FileRef(scheme="ssh", host="host", path="/opt/file.py")
        mock_adapter.read_file = AsyncMock(return_value="file content")

        content = await backend.read(ref)

        assert content == "file content"
        mock_adapter.read_file.assert_called_once_with("host", "/opt/file.py")

    @pytest.mark.asyncio
    async def test_read_file_not_found(self, backend, mock_adapter):
        """Should raise FileNotFoundError when file doesn't exist."""
        ref = FileRef(scheme="ssh", host="host", path="/opt/nonexistent.py")
        mock_adapter.read_file = AsyncMock(side_effect=FileNotFoundError("File not found"))

        with pytest.raises(FileNotFoundError):
            await backend.read(ref)

    @pytest.mark.asyncio
    async def test_read_permission_denied(self, backend, mock_adapter):
        """Should raise PermissionError when access denied."""
        ref = FileRef(scheme="ssh", host="host", path="/opt/secret.py")
        mock_adapter.read_file = AsyncMock(side_effect=PermissionError("Access denied"))

        with pytest.raises(PermissionError):
            await backend.read(ref)


class TestWrite:
    """Test write() method."""

    @pytest.mark.asyncio
    async def test_write_file(self, backend, mock_adapter):
        """Should write file content via adapter."""
        ref = FileRef(scheme="ssh", host="host", path="/opt/file.py")
        mock_adapter.write_file = AsyncMock()

        await backend.write(ref, "new content")

        mock_adapter.write_file.assert_called_once_with("host", "/opt/file.py", "new content")

    @pytest.mark.asyncio
    async def test_write_permission_denied(self, backend, mock_adapter):
        """Should raise PermissionError when write denied."""
        ref = FileRef(scheme="ssh", host="host", path="/opt/readonly.py")
        mock_adapter.write_file = AsyncMock(side_effect=PermissionError("Write denied"))

        with pytest.raises(PermissionError):
            await backend.write(ref, "content")


class TestExists:
    """Test exists() method."""

    @pytest.mark.asyncio
    async def test_exists_file_exists(self, backend, mock_adapter):
        """Should return True when file exists."""
        ref = FileRef(scheme="ssh", host="host", path="/opt/file.py")
        file_info = Mock(exists=True)
        mock_adapter.file_exists = AsyncMock(return_value=file_info)

        result = await backend.exists(ref)

        assert result is True
        mock_adapter.file_exists.assert_called_once_with("host", "/opt/file.py")

    @pytest.mark.asyncio
    async def test_exists_file_not_exists(self, backend, mock_adapter):
        """Should return False when file doesn't exist."""
        ref = FileRef(scheme="ssh", host="host", path="/opt/nonexistent.py")
        file_info = Mock(exists=False)
        mock_adapter.file_exists = AsyncMock(return_value=file_info)

        result = await backend.exists(ref)

        assert result is False


class TestListDir:
    """Test list_dir() method."""

    @pytest.mark.asyncio
    async def test_list_directory(self, backend, mock_adapter):
        """Should list directory contents as FileRefs."""
        ref = FileRef(scheme="ssh", host="host", path="/opt/dir")
        dir_info = Mock(exists=True, file_type=FileType.DIRECTORY)
        mock_adapter.file_exists = AsyncMock(return_value=dir_info)
        mock_adapter.list_directory = AsyncMock(return_value="file1.py\nfile2.py\n")

        results = await backend.list_dir(ref)

        assert len(results) == 2
        assert all(isinstance(r, FileRef) for r in results)
        assert all(r.scheme == "ssh" for r in results)
        assert all(r.host == "host" for r in results)
        assert results[0].path == "/opt/dir/file1.py"
        assert results[1].path == "/opt/dir/file2.py"

    @pytest.mark.asyncio
    async def test_list_empty_directory(self, backend, mock_adapter):
        """Should return empty list for empty directory."""
        ref = FileRef(scheme="ssh", host="host", path="/opt/empty")
        dir_info = Mock(exists=True, file_type=FileType.DIRECTORY)
        mock_adapter.file_exists = AsyncMock(return_value=dir_info)
        mock_adapter.list_directory = AsyncMock(return_value="")

        results = await backend.list_dir(ref)

        assert results == []

    @pytest.mark.asyncio
    async def test_list_nonexistent_directory(self, backend, mock_adapter):
        """Should raise FileNotFoundError when directory doesn't exist."""
        ref = FileRef(scheme="ssh", host="host", path="/opt/nonexistent")
        dir_info = Mock(exists=False)
        mock_adapter.file_exists = AsyncMock(return_value=dir_info)

        with pytest.raises(FileNotFoundError):
            await backend.list_dir(ref)

    @pytest.mark.asyncio
    async def test_list_file_not_directory(self, backend, mock_adapter):
        """Should raise NotADirectoryError when path is a file."""
        ref = FileRef(scheme="ssh", host="host", path="/opt/file.py")
        file_info = Mock(exists=True, file_type=FileType.FILE)
        mock_adapter.file_exists = AsyncMock(return_value=file_info)

        with pytest.raises(NotADirectoryError):
            await backend.list_dir(ref)
