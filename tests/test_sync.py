"""Tests for the sync module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from drive_sync.config import SyncEntry
from drive_sync.drive_client import DriveFile, DriveFolder
from drive_sync.sync import Syncer, SyncStats, extract_modified_time


@pytest.fixture
def mock_drive_client() -> MagicMock:
    """Create a mock Drive client."""
    return MagicMock()


@pytest.fixture
def syncer(mock_drive_client: MagicMock, tmp_path: Path) -> Syncer:
    """Create a Syncer instance with mocked dependencies."""
    return Syncer(mock_drive_client, tmp_path)


class TestSyncStats:
    """Tests for SyncStats dataclass."""

    def test_default_values(self) -> None:
        """Test default values are zero."""
        stats = SyncStats()
        assert stats.created == 0
        assert stats.updated == 0
        assert stats.deleted == 0
        assert stats.unchanged == 0
        assert stats.errors == 0

    def test_custom_values(self) -> None:
        """Test creating with custom values."""
        stats = SyncStats(created=5, updated=2, deleted=1, errors=1)
        assert stats.created == 5
        assert stats.updated == 2
        assert stats.deleted == 1
        assert stats.errors == 1


class TestExtractModifiedTime:
    """Tests for extract_modified_time function."""

    def test_extract_from_frontmatter(self, tmp_path: Path) -> None:
        """Test extracting modified_time from frontmatter."""
        content = """---
title: Test
modified_time: '2026-01-03T18:22:11Z'
---
Content here"""
        file_path = tmp_path / "test.md"
        file_path.write_text(content)

        assert extract_modified_time(file_path) == "2026-01-03T18:22:11Z"

    def test_extract_without_quotes(self, tmp_path: Path) -> None:
        """Test extracting modified_time without quotes."""
        content = """---
title: Test
modified_time: 2026-01-03T18:22:11Z
---
Content"""
        file_path = tmp_path / "test.md"
        file_path.write_text(content)

        assert extract_modified_time(file_path) == "2026-01-03T18:22:11Z"

    def test_returns_none_for_missing(self, tmp_path: Path) -> None:
        """Test returns None when modified_time is missing."""
        content = """---
title: Test
---
Content"""
        file_path = tmp_path / "test.md"
        file_path.write_text(content)

        assert extract_modified_time(file_path) is None

    def test_returns_none_for_nonexistent(self, tmp_path: Path) -> None:
        """Test returns None for nonexistent file."""
        assert extract_modified_time(tmp_path / "nonexistent.md") is None


class TestSyncer:
    """Tests for the Syncer class."""

    def test_sync_creates_github_folder(
        self,
        syncer: Syncer,
        mock_drive_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that sync creates the github_folder."""
        mock_drive_client.list_files.return_value = []
        mock_drive_client.list_subfolders.return_value = []

        entry = SyncEntry(drive_folder_id="folder1", github_folder="docs")
        syncer.sync_entry(entry)

        assert (tmp_path / "docs").exists()
        assert (tmp_path / "docs").is_dir()

    def test_sync_removes_existing_folder(
        self,
        syncer: Syncer,
        mock_drive_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that sync removes existing github_folder first."""
        existing_dir = tmp_path / "docs"
        existing_dir.mkdir()
        (existing_dir / "old_file.md").write_text("old content")

        mock_drive_client.list_files.return_value = []
        mock_drive_client.list_subfolders.return_value = []

        entry = SyncEntry(drive_folder_id="folder1", github_folder="docs")
        syncer.sync_entry(entry)

        assert (tmp_path / "docs").exists()
        assert not (tmp_path / "docs" / "old_file.md").exists()

    @patch("drive_sync.sync.convert_docx_to_markdown")
    def test_sync_creates_new_documents(
        self,
        mock_convert: MagicMock,
        syncer: Syncer,
        mock_drive_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that sync creates new documents."""
        mock_drive_client.list_files.return_value = [
            DriveFile(
                id="doc1",
                name="My Document",
                mime_type="application/vnd.google-apps.document",
                modified_time="2026-01-03T18:22:11Z",
            )
        ]
        mock_drive_client.list_subfolders.return_value = []
        mock_drive_client.get_docx_content.return_value = b"fake docx content"
        mock_convert.return_value = "# Converted Content"

        entry = SyncEntry(drive_folder_id="folder1", github_folder="docs")
        stats = syncer.sync_entry(entry)

        assert stats.created == 1
        assert stats.updated == 0
        assert stats.errors == 0

        output_file = tmp_path / "docs" / "my-document.md"
        assert output_file.exists()

        content = output_file.read_text()
        assert "title: My Document" in content
        assert "# Converted Content" in content

    @patch("drive_sync.sync.convert_docx_to_markdown")
    def test_sync_handles_subfolders(
        self,
        mock_convert: MagicMock,
        syncer: Syncer,
        mock_drive_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that sync handles subfolders recursively."""
        mock_drive_client.list_files.side_effect = [
            [],
            [
                DriveFile(
                    id="doc1",
                    name="Nested Doc",
                    mime_type="application/vnd.google-apps.document",
                    modified_time="2026-01-03T18:22:11Z",
                )
            ],
        ]
        mock_drive_client.list_subfolders.side_effect = [
            [DriveFolder(id="subfolder1", name="Sub Folder")],
            [],
        ]
        mock_drive_client.get_docx_content.return_value = b"fake"
        mock_convert.return_value = "content"

        entry = SyncEntry(drive_folder_id="root", github_folder="docs")
        stats = syncer.sync_entry(entry)

        assert stats.created == 1
        assert stats.folders_created == 1

        subfolder = tmp_path / "docs" / "sub-folder"
        assert subfolder.exists()
        assert (subfolder / "nested-doc.md").exists()

    @patch("drive_sync.sync.convert_docx_to_markdown")
    def test_sync_counts_errors(
        self,
        mock_convert: MagicMock,
        syncer: Syncer,
        mock_drive_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that sync counts errors properly."""
        mock_drive_client.list_files.return_value = [
            DriveFile(
                id="doc1",
                name="Bad Doc",
                mime_type="application/vnd.google-apps.document",
                modified_time="2026-01-03T18:22:11Z",
            )
        ]
        mock_drive_client.list_subfolders.return_value = []
        mock_drive_client.get_docx_content.side_effect = Exception("API Error")

        entry = SyncEntry(drive_folder_id="folder1", github_folder="docs")
        stats = syncer.sync_entry(entry)

        assert stats.created == 0
        assert stats.errors == 1

    @patch("drive_sync.sync.convert_docx_to_markdown")
    def test_sync_multiple_documents(
        self,
        mock_convert: MagicMock,
        syncer: Syncer,
        mock_drive_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test syncing multiple documents."""
        mock_drive_client.list_files.return_value = [
            DriveFile(
                id="doc1",
                name="Doc One",
                mime_type="application/vnd.google-apps.document",
                modified_time="2026-01-01T00:00:00Z",
            ),
            DriveFile(
                id="doc2",
                name="Doc Two",
                mime_type="application/vnd.google-apps.document",
                modified_time="2026-01-02T00:00:00Z",
            ),
        ]
        mock_drive_client.list_subfolders.return_value = []
        mock_drive_client.get_docx_content.return_value = b"fake"
        mock_convert.return_value = "content"

        entry = SyncEntry(drive_folder_id="folder1", github_folder="docs")
        stats = syncer.sync_entry(entry)

        assert stats.created == 2
        assert (tmp_path / "docs" / "doc-one.md").exists()
        assert (tmp_path / "docs" / "doc-two.md").exists()

    @patch("drive_sync.sync.convert_docx_to_markdown")
    def test_sync_excludes_files(
        self,
        mock_convert: MagicMock,
        syncer: Syncer,
        mock_drive_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that sync excludes files matching patterns."""
        mock_drive_client.list_files.return_value = [
            DriveFile(
                id="doc1",
                name="Keep This Doc",
                mime_type="application/vnd.google-apps.document",
                modified_time="2026-01-01T00:00:00Z",
            ),
            DriveFile(
                id="doc2",
                name="DRAFT - Ignore This",
                mime_type="application/vnd.google-apps.document",
                modified_time="2026-01-02T00:00:00Z",
            ),
            DriveFile(
                id="doc3",
                name="Another Draft Doc",
                mime_type="application/vnd.google-apps.document",
                modified_time="2026-01-03T00:00:00Z",
            ),
        ]
        mock_drive_client.list_subfolders.return_value = []
        mock_drive_client.get_docx_content.return_value = b"fake"
        mock_convert.return_value = "content"

        entry = SyncEntry(
            drive_folder_id="folder1",
            github_folder="docs",
            exclude_files=["DRAFT*", "*Draft*"],
        )
        stats = syncer.sync_entry(entry)

        assert stats.created == 1
        assert (tmp_path / "docs" / "keep-this-doc.md").exists()
        assert not (tmp_path / "docs" / "draft-ignore-this.md").exists()
        assert not (tmp_path / "docs" / "another-draft-doc.md").exists()

    @patch("drive_sync.sync.convert_docx_to_markdown")
    def test_sync_excludes_folders(
        self,
        mock_convert: MagicMock,
        syncer: Syncer,
        mock_drive_client: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Test that sync excludes folders matching patterns."""
        mock_drive_client.list_files.return_value = []
        mock_drive_client.list_subfolders.side_effect = [
            [
                DriveFolder(id="folder1", name="Keep Folder"),
                DriveFolder(id="folder2", name="Archive"),
                DriveFolder(id="folder3", name="Old Archive"),
            ],
            [],  # Keep Folder has no subfolders
        ]

        entry = SyncEntry(
            drive_folder_id="root",
            github_folder="docs",
            exclude_folders=["*Archive*"],
        )
        stats = syncer.sync_entry(entry)

        assert stats.folders_created == 1
        assert (tmp_path / "docs" / "keep-folder").exists()
        assert not (tmp_path / "docs" / "archive").exists()
        assert not (tmp_path / "docs" / "old-archive").exists()
