"""FileSnapshot entity - cached file content with dirty tracking.

Clean Architecture: Domain entity (core layer).
Represents an immutable snapshot of a file's content along with a checksum
for efficient dirty checking in world state caches.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from .file_ref import FileRef


@dataclass(frozen=True)
class FileSnapshot:
    """Immutable snapshot of a file's content with checksum and dirty flag.

    This value object represents cached file content within the world state,
    enabling efficient dirty checking via a SHA256 checksum. The entity is
    immutable (``frozen=True``); any update produces a new instance.

    Attributes:
        ref: Reference to the file location (storage-agnostic).
        content: The file's text content.
        checksum: SHA256 hex digest of ``content`` used for dirty checking.
        dirty: Modification flag indicating if content has been changed since
               it was last synchronized (defaults to ``False``).

    Examples:
        >>> ref = FileRef("file", None, "/home/user/app.py")
        >>> snap = FileSnapshot(ref, "print('hello')\n", FileSnapshot.compute_checksum("print('hello')\n"))
        >>> snap.dirty
        False

        >>> snap2 = snap.with_content("print('hi')\n")
        >>> snap2.dirty
        True
    """

    ref: FileRef
    content: str
    checksum: str
    dirty: bool = False

    @staticmethod
    def compute_checksum(content: str) -> str:
        """Compute SHA256 hex digest of given content.

        Args:
            content: Text to hash.

        Returns:
            Hexadecimal string of the SHA256 digest.
        """
        # Normalize to UTF-8 bytes for deterministic hashing
        return sha256(content.encode("utf-8")).hexdigest()

    def with_content(self, new_content: str) -> "FileSnapshot":
        """Return a new snapshot with updated content and checksum.

        The returned snapshot has ``dirty=True`` to indicate the content differs
        from the current instance.

        Args:
            new_content: New file content to set.

        Returns:
            A new ``FileSnapshot`` with updated ``content``, recomputed
            ``checksum``, and ``dirty=True``. The ``ref`` is preserved.
        """
        new_checksum = self.compute_checksum(new_content)
        return FileSnapshot(
            ref=self.ref,
            content=new_content,
            checksum=new_checksum,
            dirty=True,
        )

