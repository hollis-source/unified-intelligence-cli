"""Unit tests for FileRef entity.

Tests cover:
- URI parsing for all supported schemes (file, ssh, s3, github)
- URI serialization (to_uri) and roundtrip consistency
- Edge cases: missing host, invalid schemes, special characters
- Validation of invariants (host requirements, path requirements)
"""

import pytest
from src.entities.file_ref import FileRef


class TestFileRefParsing:
    """Test FileRef.parse() for various URI formats."""

    def test_parse_local_file_uri(self):
        """Parse local file URI: file:///home/user/app.py"""
        ref = FileRef.parse("file:///home/user/app.py")

        assert ref.scheme == "file"
        assert ref.host is None
        assert ref.path == "/home/user/app.py"

    def test_parse_ssh_uri(self):
        """Parse SSH URI: ssh://host/opt/app.py"""
        ref = FileRef.parse("ssh://syd2.jacobhollis.com/opt/grokmonster/db_status.py")

        assert ref.scheme == "ssh"
        assert ref.host == "syd2.jacobhollis.com"
        assert ref.path == "/opt/grokmonster/db_status.py"

    def test_parse_s3_uri(self):
        """Parse S3 URI: s3://bucket/key.py"""
        ref = FileRef.parse("s3://my-bucket/data/file.csv")

        assert ref.scheme == "s3"
        assert ref.host == "my-bucket"
        assert ref.path == "/data/file.csv"

    def test_parse_s3_uri_without_leading_slash(self):
        """Parse S3 URI without leading slash: s3://bucket/key"""
        ref = FileRef.parse("s3://bucket/key.py")

        assert ref.scheme == "s3"
        assert ref.host == "bucket"
        # Should add leading slash automatically
        assert ref.path == "/key.py"

    def test_parse_github_uri(self):
        """Parse GitHub URI: github://org/repo/path"""
        ref = FileRef.parse("github://myorg/myrepo/src/main.py")

        assert ref.scheme == "github"
        assert ref.host == "myorg"
        assert ref.path == "/myrepo/src/main.py"

    def test_parse_path_with_spaces(self):
        """Parse URI with spaces in path"""
        ref = FileRef.parse("file:///home/user/my%20file.py")

        assert ref.scheme == "file"
        assert ref.path == "/home/user/my%20file.py"

    def test_parse_path_with_special_chars(self):
        """Parse URI with special characters in path"""
        ref = FileRef.parse("ssh://host/opt/app-v1.2.3_beta.py")

        assert ref.scheme == "ssh"
        assert ref.host == "host"
        assert ref.path == "/opt/app-v1.2.3_beta.py"

    def test_parse_empty_uri_raises_error(self):
        """Parse empty URI should raise ValueError"""
        with pytest.raises(ValueError, match="URI cannot be empty"):
            FileRef.parse("")

    def test_parse_uri_without_scheme_raises_error(self):
        """Parse URI without scheme should raise ValueError"""
        with pytest.raises(ValueError, match="missing scheme"):
            FileRef.parse("/home/user/app.py")

    def test_parse_uri_without_path_raises_error(self):
        """Parse URI without path should raise ValueError"""
        with pytest.raises(ValueError, match="missing path"):
            FileRef.parse("file://")

    def test_parse_file_uri_with_relative_path_raises_error(self):
        """Parse file:// URI with relative path should raise ValueError"""
        with pytest.raises(ValueError, match="must have absolute path"):
            FileRef.parse("file://relative/path.py")


class TestFileRefSerialization:
    """Test FileRef.to_uri() serialization."""

    def test_to_uri_local_file(self):
        """Serialize local file FileRef to URI"""
        ref = FileRef("file", None, "/home/user/app.py")
        uri = ref.to_uri()

        assert uri == "file:///home/user/app.py"

    def test_to_uri_ssh(self):
        """Serialize SSH FileRef to URI"""
        ref = FileRef("ssh", "syd2.jacobhollis.com", "/opt/grokmonster/db_status.py")
        uri = ref.to_uri()

        assert uri == "ssh://syd2.jacobhollis.com/opt/grokmonster/db_status.py"

    def test_to_uri_s3(self):
        """Serialize S3 FileRef to URI"""
        ref = FileRef("s3", "my-bucket", "/data/file.csv")
        uri = ref.to_uri()

        assert uri == "s3://my-bucket/data/file.csv"

    def test_to_uri_github(self):
        """Serialize GitHub FileRef to URI"""
        ref = FileRef("github", "myorg", "/myrepo/src/main.py")
        uri = ref.to_uri()

        assert uri == "github://myorg/myrepo/src/main.py"


class TestFileRefRoundtrip:
    """Test parse → to_uri roundtrip consistency."""

    def test_roundtrip_local_file(self):
        """Roundtrip: parse(uri).to_uri() == uri for local file"""
        uri = "file:///home/user/app.py"
        ref = FileRef.parse(uri)

        assert ref.to_uri() == uri

    def test_roundtrip_ssh(self):
        """Roundtrip: parse(uri).to_uri() == uri for SSH"""
        uri = "ssh://host/opt/app.py"
        ref = FileRef.parse(uri)

        assert ref.to_uri() == uri

    def test_roundtrip_s3(self):
        """Roundtrip: parse(uri).to_uri() == uri for S3"""
        uri = "s3://bucket/key.py"
        ref = FileRef.parse(uri)

        # Note: S3 URI gets normalized with leading slash
        assert ref.to_uri() == "s3://bucket/key.py"

    def test_roundtrip_github(self):
        """Roundtrip: parse(uri).to_uri() == uri for GitHub"""
        uri = "github://org/repo/path.py"
        ref = FileRef.parse(uri)

        assert ref.to_uri() == "github://org/repo/path.py"


class TestFileRefValidation:
    """Test FileRef validation and invariants."""

    def test_invalid_scheme_raises_error(self):
        """Creating FileRef with invalid scheme should raise ValueError"""
        with pytest.raises(ValueError, match="Invalid scheme"):
            FileRef("ftp", "host", "/path")

    def test_file_scheme_with_host_raises_error(self):
        """file:// scheme with host should raise ValueError"""
        with pytest.raises(ValueError, match="must not have a host"):
            FileRef("file", "localhost", "/home/user/app.py")

    def test_ssh_scheme_without_host_raises_error(self):
        """ssh:// scheme without host should raise ValueError"""
        with pytest.raises(ValueError, match="requires a host"):
            FileRef("ssh", None, "/opt/app.py")

    def test_s3_scheme_without_host_raises_error(self):
        """s3:// scheme without host should raise ValueError"""
        with pytest.raises(ValueError, match="requires a host"):
            FileRef("s3", None, "/bucket/key.py")

    def test_github_scheme_without_host_raises_error(self):
        """github:// scheme without host should raise ValueError"""
        with pytest.raises(ValueError, match="requires a host"):
            FileRef("github", None, "/org/repo/path.py")

    def test_empty_path_raises_error(self):
        """Empty path should raise ValueError"""
        with pytest.raises(ValueError, match="path cannot be empty"):
            FileRef("file", None, "")


class TestFileRefImmutability:
    """Test FileRef immutability (frozen dataclass)."""

    def test_fileref_is_immutable(self):
        """FileRef should be immutable (frozen=True)"""
        ref = FileRef("file", None, "/home/user/app.py")

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            ref.path = "/new/path"

    def test_fileref_is_hashable(self):
        """FileRef should be hashable (can be used in sets/dicts)"""
        ref1 = FileRef("file", None, "/home/user/app.py")
        ref2 = FileRef("file", None, "/home/user/app.py")
        ref3 = FileRef("ssh", "host", "/opt/app.py")

        # Should be able to create set
        refs = {ref1, ref2, ref3}
        assert len(refs) == 2  # ref1 and ref2 are equal

        # Should be able to use as dict key
        cache = {ref1: "content"}
        assert cache[ref2] == "content"


class TestFileRefStringRepresentation:
    """Test FileRef string representations."""

    def test_str_returns_uri(self):
        """str(FileRef) should return URI format"""
        ref = FileRef("ssh", "host", "/opt/app.py")

        assert str(ref) == "ssh://host/opt/app.py"

    def test_repr_shows_components(self):
        """repr(FileRef) should show scheme/host/path components"""
        ref = FileRef("file", None, "/home/user/app.py")

        repr_str = repr(ref)
        assert "FileRef" in repr_str
        assert "scheme='file'" in repr_str
        assert "host=None" in repr_str
        assert "path='/home/user/app.py'" in repr_str

