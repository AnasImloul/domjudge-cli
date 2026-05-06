"""Tests for filesystem helpers in dom.utils.sys."""

from dom.utils.sys import load_folder_as_dict


class TestLoadFolderAsDict:
    """Tests for load_folder_as_dict."""

    def test_returns_empty_dict_when_path_missing(self, temp_dir):
        """Missing directories should produce an empty dict, not an error."""
        missing = temp_dir / "does-not-exist"
        assert load_folder_as_dict(missing) == {}

    def test_reads_files_keyed_by_filename(self, temp_dir):
        """Files in the directory should be loaded with their bytes."""
        (temp_dir / "a.txt").write_bytes(b"alpha")
        (temp_dir / "b.txt").write_bytes(b"beta")

        result = load_folder_as_dict(temp_dir)

        assert result == {"a.txt": b"alpha", "b.txt": b"beta"}

    def test_skips_subdirectories(self, temp_dir):
        """Nested directories should be ignored — only top-level files load."""
        (temp_dir / "file.txt").write_bytes(b"top")
        nested = temp_dir / "sub"
        nested.mkdir()
        (nested / "ignored.txt").write_bytes(b"deep")

        result = load_folder_as_dict(temp_dir)

        assert result == {"file.txt": b"top"}
