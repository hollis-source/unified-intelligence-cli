"""FileRef Entity - Normalized file identifier with scheme/host/path.

Clean Architecture: Core entity (innermost layer, no dependencies).
SOLID: SRP - single responsibility of representing file references.

This entity represents a file reference that can point to local or remote files
using URI schemes (file://, ssh://, s3://, github://).
"""

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse, urlunparse


@dataclass(frozen=True)
class FileRef:
    """Immutable file reference with scheme/host/path components.

    Represents a normalized file identifier that can reference files across
    different storage backends (local filesystem, SSH, S3, GitHub, etc.).

    Attributes:
        scheme: URI scheme identifying the storage backend
                ("file", "ssh", "s3", "github")
        host: Optional hostname for remote schemes (required for ssh/s3/github,
              None for local file://)
        path: Absolute path to the file within the storage backend

    Examples:
        >>> FileRef("file", None, "/home/user/app.py")
        FileRef(scheme='file', host=None, path='/home/user/app.py')

        >>> FileRef("ssh", "syd2.jacobhollis.com", "/opt/grokmonster/db_status.py")
        FileRef(scheme='ssh', host='syd2.jacobhollis.com', path='/opt/grokmonster/db_status.py')

        >>> FileRef("s3", "my-bucket", "/data/file.csv")
        FileRef(scheme='s3', host='my-bucket', path='/data/file.csv')
    """

    scheme: str
    host: Optional[str]
    path: str

    def __post_init__(self) -> None:
        """Validate FileRef invariants after initialization.

        Raises:
            ValueError: If scheme is invalid or host requirements are violated
        """
        # Validate scheme
        valid_schemes = {"file", "ssh", "s3", "github"}
        if self.scheme not in valid_schemes:
            raise ValueError(
                f"Invalid scheme '{self.scheme}'. "
                f"Must be one of: {', '.join(sorted(valid_schemes))}"
            )

        # Validate host requirements
        if self.scheme == "file" and self.host is not None:
            raise ValueError(
                f"file:// scheme must not have a host (got '{self.host}')"
            )

        if self.scheme in {"ssh", "s3", "github"} and not self.host:
            raise ValueError(
                f"{self.scheme}:// scheme requires a host"
            )

        # Validate path
        if not self.path:
            raise ValueError("path cannot be empty")

    @classmethod
    def parse(cls, uri: str) -> "FileRef":
        """Parse a URI string into a FileRef.

        Supports the following URI formats:
        - file:///absolute/path (local filesystem)
        - ssh://hostname/absolute/path (SSH remote)
        - s3://bucket/key (S3 object storage)
        - github://org/repo/path (GitHub repository)

        Args:
            uri: URI string to parse

        Returns:
            FileRef instance with parsed components

        Raises:
            ValueError: If URI is invalid or cannot be parsed

        Examples:
            >>> FileRef.parse("file:///home/user/app.py")
            FileRef(scheme='file', host=None, path='/home/user/app.py')

            >>> FileRef.parse("ssh://host/opt/app.py")
            FileRef(scheme='ssh', host='host', path='/opt/app.py')

            >>> FileRef.parse("s3://bucket/key.py")
            FileRef(scheme='s3', host='bucket', path='/key.py')
        """
        if not uri:
            raise ValueError("URI cannot be empty")

        try:
            parsed = urlparse(uri)
        except Exception as e:
            raise ValueError(f"Failed to parse URI '{uri}': {e}") from e

        if not parsed.scheme:
            raise ValueError(
                f"URI '{uri}' missing scheme. "
                f"Expected format: scheme://[host]/path"
            )

        scheme = parsed.scheme.lower()
        host = parsed.netloc if parsed.netloc else None
        path = parsed.path

        # Handle empty path
        if not path:
            raise ValueError(f"URI '{uri}' missing path component")

        # For file:// URIs, ensure path is absolute and no host
        if scheme == "file":
            if host:
                # file://relative/path.py gets parsed as host="relative", path="/path.py"
                # This is invalid - file:// should be file:///absolute/path
                raise ValueError(
                    f"file:// URI must have absolute path (got '{uri}'). "
                    f"Use file:///absolute/path format"
                )
            if not path.startswith("/"):
                raise ValueError(
                    f"file:// URI must have absolute path (got '{path}')"
                )

        # For remote schemes, ensure path is absolute
        if scheme in {"ssh", "s3", "github"}:
            if not path.startswith("/"):
                # S3 and GitHub often omit leading slash, add it
                path = "/" + path

        return cls(scheme=scheme, host=host, path=path)

    def to_uri(self) -> str:
        """Convert FileRef back to URI string.

        Returns:
            URI string representation of this FileRef

        Examples:
            >>> ref = FileRef("file", None, "/home/user/app.py")
            >>> ref.to_uri()
            'file:///home/user/app.py'

            >>> ref = FileRef("ssh", "host", "/opt/app.py")
            >>> ref.to_uri()
            'ssh://host/opt/app.py'
        """
        if self.scheme == "file":
            # file:// URIs have no netloc, path starts with /
            return urlunparse((self.scheme, "", self.path, "", "", ""))
        else:
            # Remote schemes have netloc (host)
            netloc = self.host or ""
            return urlunparse((self.scheme, netloc, self.path, "", "", ""))

    def __str__(self) -> str:
        """String representation returns URI format."""
        return self.to_uri()

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return f"FileRef(scheme={self.scheme!r}, host={self.host!r}, path={self.path!r})"

