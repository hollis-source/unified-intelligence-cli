"""Unit tests for FileSnapshot entity.

Covers:
- SHA256 checksum computation
- Immutability and value semantics
- with_content behavior (content, checksum, dirty flag)
"""

import pytest

from src.core.entities.file_ref import FileRef
from src.core.entities.file_snapshot import FileSnapshot


class TestFileSnapshotBasics:
    def test_compute_checksum_known_value(self):
        content = "hello"
        # Known SHA256 for "hello"
        assert (
            FileSnapshot.compute_checksum(content)
            == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        )

    def test_create_snapshot_and_fields(self):
        ref = FileRef("file", None, "/tmp/example.txt")
        content = "print('hello')\n"
        checksum = FileSnapshot.compute_checksum(content)

        snap = FileSnapshot(ref=ref, content=content, checksum=checksum)

        assert snap.ref == ref
        assert snap.content == content
        assert snap.checksum == checksum
        assert snap.dirty is False


class TestFileSnapshotImmutability:
    def test_snapshot_is_immutable(self):
        ref = FileRef("file", None, "/tmp/example.txt")
        snap = FileSnapshot(ref, "data", FileSnapshot.compute_checksum("data"))

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            snap.content = "new"


class TestWithContent:
    def test_with_content_returns_new_instance_and_sets_dirty(self):
        ref = FileRef("file", None, "/tmp/example.txt")
        snap = FileSnapshot(ref, "one", FileSnapshot.compute_checksum("one"))

        new_snap = snap.with_content("two")

        assert new_snap is not snap
        assert new_snap.ref == ref
        assert new_snap.content == "two"
        assert (
            new_snap.checksum == FileSnapshot.compute_checksum("two")
        )
        assert new_snap.dirty is True

        # Original remains unchanged
        assert snap.content == "one"
        assert snap.dirty is False

    def test_with_content_idempotent_checksum(self):
        ref = FileRef("file", None, "/tmp/example.txt")
        content = "abc\n"
        snap = FileSnapshot(ref, content, FileSnapshot.compute_checksum(content))

        # Updating with the same content should still mark as dirty (explicit change)
        new_snap = snap.with_content(content)
        assert new_snap.checksum == snap.checksum
        assert new_snap.dirty is True

