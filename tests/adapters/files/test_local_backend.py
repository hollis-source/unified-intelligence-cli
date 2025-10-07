"""Tests for LocalBackend - local filesystem adapter."""

import pytest
from pathlib import Path
from src.adapters.files.local_backend import LocalBackend
from src.core.entities.file_ref import FileRef


@pytest.fixture
def backend():
    """Create LocalBackend instance."""
    return LocalBackend()


@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file with content."""
    file = tmp_path / "test.txt"
    file.write_text("test content", encoding="utf-8")
    return file


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory with some files."""
    dir_path = tmp_path / "test_dir"
    dir_path.mkdir()
    (dir_path / "file1.txt").write_text("content1")
    (dir_path / "file2.txt").write_text("content2")
    return dir_path


class TestSupports:
    """Test supports() method."""

    @pytest.mark.asyncio
    async def test_supports_file_scheme(self, backend):
        """Should support file:// scheme."""
        ref = FileRef(scheme="file", host=None, path="/tmp/test.txt")
        assert backend.supports(ref) is True

    @pytest.mark.asyncio
    async def test_rejects_ssh_scheme(self, backend):
        """Should reject ssh:// scheme."""
        ref = FileRef(scheme="ssh", host="host", path="/tmp/test.txt")
        assert backend.supports(ref) is False

    @pytest.mark.asyncio
    async def test_rejects_s3_scheme(self, backend):
        """Should reject s3:// scheme."""
        ref = FileRef(scheme="s3", host="bucket", path="/key/file.txt")
        assert backend.supports(ref) is False


class TestRead:
    """Test read() method."""

    @pytest.mark.asyncio
    async def test_read_existing_file(self, backend, temp_file):
        """Should read content from existing file."""
        ref = FileRef(scheme="file", host=None, path=str(temp_file))
        content = await backend.read(ref)
        assert content == "test content"

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, backend, tmp_path):
        """Should raise FileNotFoundError for nonexistent file."""
        ref = FileRef(scheme="file", host=None, path=str(tmp_path / "nonexistent.txt"))
        with pytest.raises(FileNotFoundError):
            await backend.read(ref)


class TestWrite:
    """Test write() method."""

    @pytest.mark.asyncio
    async def test_write_new_file(self, backend, tmp_path):
        """Should create new file with content."""
        file_path = tmp_path / "new_file.txt"
        ref = FileRef(scheme="file", host=None, path=str(file_path))
        await backend.write(ref, "new content")
        assert file_path.read_text() == "new content"

    @pytest.mark.asyncio
    async def test_write_overwrite_existing(self, backend, temp_file):
        """Should overwrite existing file."""
        ref = FileRef(scheme="file", host=None, path=str(temp_file))
        await backend.write(ref, "overwritten")
        assert temp_file.read_text() == "overwritten"

    @pytest.mark.asyncio
    async def test_write_creates_parent_dirs(self, backend, tmp_path):
        """Should create parent directories if they don't exist."""
        file_path = tmp_path / "subdir" / "nested" / "file.txt"
        ref = FileRef(scheme="file", host=None, path=str(file_path))
        await backend.write(ref, "content")
        assert file_path.exists()
        assert file_path.read_text() == "content"


class TestExists:
    """Test exists() method."""

    @pytest.mark.asyncio
    async def test_exists_for_existing_file(self, backend, temp_file):
        """Should return True for existing file."""
        ref = FileRef(scheme="file", host=None, path=str(temp_file))
        assert await backend.exists(ref) is True

    @pytest.mark.asyncio
    async def test_exists_for_existing_dir(self, backend, temp_dir):
        """Should return True for existing directory."""
        ref = FileRef(scheme="file", host=None, path=str(temp_dir))
        assert await backend.exists(ref) is True

    @pytest.mark.asyncio
    async def test_exists_for_nonexistent(self, backend, tmp_path):
        """Should return False for nonexistent path."""
        ref = FileRef(scheme="file", host=None, path=str(tmp_path / "nonexistent"))
        assert await backend.exists(ref) is False


class TestListDir:
    """Test list_dir() method."""

    @pytest.mark.asyncio
    async def test_list_directory(self, backend, temp_dir):
        """Should list directory contents as FileRefs."""
        ref = FileRef(scheme="file", host=None, path=str(temp_dir))
        results = await backend.list_dir(ref)

        assert len(results) == 2
        assert all(isinstance(r, FileRef) for r in results)
        assert all(r.scheme == "file" for r in results)
        assert all(r.host is None for r in results)

        # Check that file paths are absolute and match expected files
        paths = {Path(r.path).name for r in results}
        assert paths == {"file1.txt", "file2.txt"}

    @pytest.mark.asyncio
    async def test_list_empty_directory(self, backend, tmp_path):
        """Should return empty list for empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        ref = FileRef(scheme="file", host=None, path=str(empty_dir))
        results = await backend.list_dir(ref)
        assert results == []

    @pytest.mark.asyncio
    async def test_list_nonexistent_directory(self, backend, tmp_path):
        """Should raise FileNotFoundError for nonexistent directory."""
        ref = FileRef(scheme="file", host=None, path=str(tmp_path / "nonexistent"))
        with pytest.raises(FileNotFoundError):
            await backend.list_dir(ref)

    @pytest.mark.asyncio
    async def test_list_file_not_directory(self, backend, temp_file):
        """Should raise NotADirectoryError when listing a file."""
        ref = FileRef(scheme="file", host=None, path=str(temp_file))
        with pytest.raises(NotADirectoryError):
            await backend.list_dir(ref)
