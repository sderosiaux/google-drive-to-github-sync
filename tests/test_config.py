"""Tests for the config module."""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from drive_sync.config import Config, SyncEntry, load_config


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self, tmp_path: Path) -> None:
        """Test loading a valid configuration file."""
        config_content = """
sync:
  - drive_folder_id: "folder1"
    github_folder: "docs"
  - drive_folder_id: "folder2"
    github_folder: "notes"
"""
        config_file = tmp_path / ".drive-sync.yml"
        config_file.write_text(config_content)

        config = load_config(config_file)

        assert len(config.sync) == 2
        assert config.sync[0].drive_folder_id == "folder1"
        assert config.sync[0].github_folder == "docs"
        assert config.sync[1].drive_folder_id == "folder2"
        assert config.sync[1].github_folder == "notes"

    def test_load_single_entry(self, tmp_path: Path) -> None:
        """Test loading a config with a single entry."""
        config_content = """
sync:
  - drive_folder_id: "abc123"
    github_folder: "product-docs"
"""
        config_file = tmp_path / ".drive-sync.yml"
        config_file.write_text(config_content)

        config = load_config(config_file)

        assert len(config.sync) == 1
        assert config.sync[0].drive_folder_id == "abc123"
        assert config.sync[0].github_folder == "product-docs"

    def test_file_not_found(self) -> None:
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError):
            load_config(Path("/nonexistent/.drive-sync.yml"))

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test that ValueError is raised for empty file."""
        config_file = tmp_path / ".drive-sync.yml"
        config_file.write_text("")

        with pytest.raises(ValueError, match="empty"):
            load_config(config_file)

    def test_missing_sync_key(self, tmp_path: Path) -> None:
        """Test that ValueError is raised when sync key is missing."""
        config_content = """
other_key:
  - value: "test"
"""
        config_file = tmp_path / ".drive-sync.yml"
        config_file.write_text(config_content)

        with pytest.raises(ValueError, match="'sync' key"):
            load_config(config_file)

    def test_sync_not_list(self, tmp_path: Path) -> None:
        """Test that ValueError is raised when sync is not a list."""
        config_content = """
sync:
  drive_folder_id: "test"
"""
        config_file = tmp_path / ".drive-sync.yml"
        config_file.write_text(config_content)

        with pytest.raises(ValueError, match="must be a list"):
            load_config(config_file)

    def test_missing_drive_folder_id(self, tmp_path: Path) -> None:
        """Test that ValueError is raised when drive_folder_id is missing."""
        config_content = """
sync:
  - github_folder: "docs"
"""
        config_file = tmp_path / ".drive-sync.yml"
        config_file.write_text(config_content)

        with pytest.raises(ValueError, match="drive_folder_id"):
            load_config(config_file)

    def test_missing_github_folder(self, tmp_path: Path) -> None:
        """Test that ValueError is raised when github_folder is missing."""
        config_content = """
sync:
  - drive_folder_id: "abc123"
"""
        config_file = tmp_path / ".drive-sync.yml"
        config_file.write_text(config_content)

        with pytest.raises(ValueError, match="github_folder"):
            load_config(config_file)

    def test_entry_not_mapping(self, tmp_path: Path) -> None:
        """Test that ValueError is raised when entry is not a mapping."""
        config_content = """
sync:
  - "just a string"
"""
        config_file = tmp_path / ".drive-sync.yml"
        config_file.write_text(config_content)

        with pytest.raises(ValueError, match="must be a mapping"):
            load_config(config_file)


class TestSyncEntry:
    """Tests for SyncEntry dataclass."""

    def test_create_sync_entry(self) -> None:
        """Test creating a SyncEntry."""
        entry = SyncEntry(
            drive_folder_id="abc123",
            github_folder="docs",
        )

        assert entry.drive_folder_id == "abc123"
        assert entry.github_folder == "docs"

    def test_create_sync_entry_with_excludes(self) -> None:
        """Test creating a SyncEntry with exclusions."""
        entry = SyncEntry(
            drive_folder_id="abc123",
            github_folder="docs",
            exclude_folders=["Archive", "Old*"],
            exclude_files=["DRAFT*", "*.tmp"],
        )

        assert entry.exclude_folders == ["Archive", "Old*"]
        assert entry.exclude_files == ["DRAFT*", "*.tmp"]

    def test_is_folder_excluded_exact_match(self) -> None:
        """Test folder exclusion with exact match."""
        entry = SyncEntry(
            drive_folder_id="abc123",
            github_folder="docs",
            exclude_folders=["Archive"],
        )

        assert entry.is_folder_excluded("Archive") is True
        assert entry.is_folder_excluded("archive") is True  # case insensitive
        assert entry.is_folder_excluded("Other") is False

    def test_is_folder_excluded_glob_pattern(self) -> None:
        """Test folder exclusion with glob patterns."""
        entry = SyncEntry(
            drive_folder_id="abc123",
            github_folder="docs",
            exclude_folders=["*Archive*", "Old*"],
        )

        assert entry.is_folder_excluded("Archive") is True
        assert entry.is_folder_excluded("Old Archive") is True
        assert entry.is_folder_excluded("My Archive Folder") is True
        assert entry.is_folder_excluded("Old Stuff") is True
        assert entry.is_folder_excluded("New Stuff") is False

    def test_is_file_excluded_exact_match(self) -> None:
        """Test file exclusion with exact match."""
        entry = SyncEntry(
            drive_folder_id="abc123",
            github_folder="docs",
            exclude_files=["README.md"],
        )

        assert entry.is_file_excluded("README.md") is True
        assert entry.is_file_excluded("readme.md") is True  # case insensitive
        assert entry.is_file_excluded("Other.md") is False

    def test_is_file_excluded_glob_pattern(self) -> None:
        """Test file exclusion with glob patterns."""
        entry = SyncEntry(
            drive_folder_id="abc123",
            github_folder="docs",
            exclude_files=["DRAFT*", "*-backup*", "*.tmp"],
        )

        assert entry.is_file_excluded("DRAFT Document") is True
        assert entry.is_file_excluded("DRAFT - Something") is True
        assert entry.is_file_excluded("my-backup-file") is True
        assert entry.is_file_excluded("file.tmp") is True
        assert entry.is_file_excluded("Final Document") is False


class TestConfig:
    """Tests for Config dataclass."""

    def test_create_config(self) -> None:
        """Test creating a Config."""
        entries = [
            SyncEntry(drive_folder_id="a", github_folder="x"),
            SyncEntry(drive_folder_id="b", github_folder="y"),
        ]
        config = Config(sync=entries)

        assert len(config.sync) == 2
        assert config.sync[0].drive_folder_id == "a"
        assert config.sync[1].github_folder == "y"
