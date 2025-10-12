"""FileRef entity - normalized file identifier with scheme/host/path.

Clean Architecture: Domain entity (core layer).
Represents a file reference that can be local, remote SSH, S3, GitHub, etc.
"""

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse, urlunparse


@dataclass(frozen=True)
class FileRef:
    """Normalized file identifier with scheme/host/path.

    Represents a file location across different storage backends using URI syntax.
    Immutable value object following DDD principles.

    Supported schemes:
        - file: Local filesystem (file:///path/to/file)
        - ssh: Remote SSH/SFTP (ssh://host/path/to/file)
        - s3: AWS S3 (s3://bucket/key/to/file)
        - github: GitHub repository (github://org/repo/path/to/file)

    Attributes:
        scheme: Protocol/storage type ("file", "ssh", "s3", "github")
        host: Host/server name (None for local files, required for ssh/s3/github)
        path: File path on the storage backend

    Examples:
        >>> FileRef("file", None, "/home/user/app.py")
        FileRef(scheme='file', host=None, path='/home/user/app.py')

        >>> FileRef("ssh", "syd2.jacobhollis.com", "/opt/grokmonster/app.py")
        FileRef(scheme='ssh', host='syd2.jacobhollis.com', path='/opt/grokmonster/app.py')

        >>> FileRef.parse("ssh://host/opt/app.py")
        FileRef(scheme='ssh', host='host', path='/opt/app.py')
    """

    scheme: str
    host: Optional[str]
    path: str

    def __post_init__(self):
        """Validate FileRef after initialization."""
        # Validate scheme
        valid_schemes = {"file", "ssh", "s3", "github", "http", "https"}
        if self.scheme not in valid_schemes:
            raise ValueError(
                f"Invalid scheme '{self.scheme}'. "
                f"Supported: {', '.join(sorted(valid_schemes))}"
            )

        # Validate host requirements
        if self.scheme in {"ssh", "s3", "github"} and not self.host:
            raise ValueError(f"Scheme '{self.scheme}' requires a host")

        # Validate path
        if not self.path:
            raise ValueError("Path cannot be empty")

    @classmethod
    def parse(cls, uri: str) -> "FileRef":
        """Parse URI string into FileRef.

        Supports various URI formats:
            - file:///absolute/path
            - ssh://user@host/path  (user@ handled by SSH backend)
            - ssh://host/path
            - s3://bucket/key/path
            - github://org/repo/branch/path

        Args:
            uri: URI string to parse

        Returns:
            FileRef instance

        Raises:
            ValueError: If URI is invalid or malformed

        Examples:
            >>> FileRef.parse("file:///home/user/app.py")
            FileRef(scheme='file', host=None, path='/home/user/app.py')

            >>> FileRef.parse("ssh://syd2.example.com/opt/app.py")
            FileRef(scheme='ssh', host='syd2.example.com', path='/opt/app.py')

            >>> FileRef.parse("s3://my-bucket/data/file.csv")
            FileRef(scheme='s3', host='my-bucket', path='/data/file.csv')
        """
        if not uri:
            raise ValueError("URI cannot be empty")

        try:
            parsed = urlparse(uri)
        except Exception as e:
            raise ValueError(f"Failed to parse URI '{uri}': {e}")

        scheme = parsed.scheme
        if not scheme:
            raise ValueError(f"URI must include scheme (e.g., file://, ssh://): '{uri}'")

        # Extract host (None for file://)
        host = parsed.netloc if parsed.netloc else None

        # Extract path
        path = parsed.path
        if not path:
            raise ValueError(f"URI must include path: '{uri}'")

        # For file:// URIs, path should be absolute
        if scheme == "file" and not path.startswith("/"):
            raise ValueError(f"file:// URIs must have absolute paths: '{uri}'")

        return cls(scheme=scheme, host=host, path=path)

    def to_uri(self) -> str:
        """Convert FileRef to URI string.

        Returns:
            URI string representation

        Examples:
            >>> ref = FileRef("file", None, "/home/user/app.py")
            >>> ref.to_uri()
            'file:///home/user/app.py'

            >>> ref = FileRef("ssh", "host", "/opt/app.py")
            >>> ref.to_uri()
            'ssh://host/opt/app.py'
        """
        # Build netloc (host part)
        netloc = self.host if self.host else ""

        # Use urlunparse for proper URI construction
        return urlunparse((
            self.scheme,  # scheme
            netloc,       # netloc (host)
            self.path,    # path
            "",           # params
            "",           # query
            ""            # fragment
        ))

    def __str__(self) -> str:
        """String representation (URI format)."""
        return self.to_uri()

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"FileRef(scheme={self.scheme!r}, host={self.host!r}, path={self.path!r})"
