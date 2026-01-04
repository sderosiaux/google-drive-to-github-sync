"""Tests for the drive_client module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from drive_sync.drive_client import (
    DOCX_MIME_TYPE,
    GOOGLE_DOC_MIME_TYPE,
    GOOGLE_FOLDER_MIME_TYPE,
    DriveClient,
    DriveFile,
    DriveFolder,
)


class TestDriveFile:
    """Tests for DriveFile dataclass."""

    def test_create_drive_file(self) -> None:
        """Test creating a DriveFile."""
        file = DriveFile(
            id="abc123",
            name="Test Doc",
            mime_type=GOOGLE_DOC_MIME_TYPE,
            modified_time="2026-01-03T18:22:11Z",
        )

        assert file.id == "abc123"
        assert file.name == "Test Doc"
        assert file.mime_type == GOOGLE_DOC_MIME_TYPE
        assert file.modified_time == "2026-01-03T18:22:11Z"


class TestDriveFolder:
    """Tests for DriveFolder dataclass."""

    def test_create_drive_folder(self) -> None:
        """Test creating a DriveFolder."""
        folder = DriveFolder(id="xyz789", name="My Folder")

        assert folder.id == "xyz789"
        assert folder.name == "My Folder"


class TestDriveClient:
    """Tests for DriveClient class."""

    @pytest.fixture
    def mock_credentials_json(self) -> str:
        """Create mock service account credentials JSON."""
        return json.dumps(
            {
                "type": "service_account",
                "project_id": "test-project",
                "private_key_id": "key123",
                "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIBogIBAAJBALRiMLAHudeSA2ai6k5NIJyfPMfpubVOXIw6Omni8G2XxPzTL/Ho\nDz9IxhNfFtF3vIo4nDADLIJcB8s+JMiWrz8CAwEAAQJAGxnYvCrSvVMmzxSWLxMW\nQGbEw5gCvbLc/Dk5m8HwPDJg8v+kJT3K/L8VdGZCYRNg9kA3z0pmWtqP/mYVxMnp\n0QIhAOMN0u4XU85jNvXPYfKtZJuQRq+h2fgWcvfGbAbKUIy7AiEAy5MqJvxA7/bX\nrG1oB76dBU+qwoIhFw0LJR2C+KGLv5kCIF97XPAO8bNJYHKwAWdHTK/pVdB0hECp\nZRVpw4LI8jbzAiEAi9nEcFCc6L5fBJ+U4FKCt4SFP8Y6e4UuHQRnGH+4thECICIB\nCaHTJIOB8AxKSKoXpQm7oQq2N5sTB3Q5wSZ1lM3o\n-----END RSA PRIVATE KEY-----\n",
                "client_email": "test@test-project.iam.gserviceaccount.com",
                "client_id": "123456789",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        )

    @patch("drive_sync.drive_client.build")
    @patch("drive_sync.drive_client.service_account.Credentials.from_service_account_info")
    def test_list_files(
        self,
        mock_creds: MagicMock,
        mock_build: MagicMock,
        mock_credentials_json: str,
    ) -> None:
        """Test listing files in a folder."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.files().list().execute.return_value = {
            "files": [
                {
                    "id": "doc1",
                    "name": "Document 1",
                    "mimeType": GOOGLE_DOC_MIME_TYPE,
                    "modifiedTime": "2026-01-01T00:00:00Z",
                },
                {
                    "id": "doc2",
                    "name": "Document 2",
                    "mimeType": GOOGLE_DOC_MIME_TYPE,
                    "modifiedTime": "2026-01-02T00:00:00Z",
                },
            ]
        }

        client = DriveClient(mock_credentials_json)
        files = client.list_files("folder123")

        assert len(files) == 2
        assert files[0].id == "doc1"
        assert files[0].name == "Document 1"
        assert files[1].id == "doc2"

    @patch("drive_sync.drive_client.build")
    @patch("drive_sync.drive_client.service_account.Credentials.from_service_account_info")
    def test_list_files_pagination(
        self,
        mock_creds: MagicMock,
        mock_build: MagicMock,
        mock_credentials_json: str,
    ) -> None:
        """Test listing files with pagination."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.files().list().execute.side_effect = [
            {
                "files": [
                    {
                        "id": "doc1",
                        "name": "Doc 1",
                        "mimeType": GOOGLE_DOC_MIME_TYPE,
                        "modifiedTime": "2026-01-01T00:00:00Z",
                    }
                ],
                "nextPageToken": "token123",
            },
            {
                "files": [
                    {
                        "id": "doc2",
                        "name": "Doc 2",
                        "mimeType": GOOGLE_DOC_MIME_TYPE,
                        "modifiedTime": "2026-01-02T00:00:00Z",
                    }
                ],
            },
        ]

        client = DriveClient(mock_credentials_json)
        files = client.list_files("folder123")

        assert len(files) == 2

    @patch("drive_sync.drive_client.build")
    @patch("drive_sync.drive_client.service_account.Credentials.from_service_account_info")
    def test_list_subfolders(
        self,
        mock_creds: MagicMock,
        mock_build: MagicMock,
        mock_credentials_json: str,
    ) -> None:
        """Test listing subfolders."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.files().list().execute.return_value = {
            "files": [
                {"id": "folder1", "name": "Subfolder 1"},
                {"id": "folder2", "name": "Subfolder 2"},
            ]
        }

        client = DriveClient(mock_credentials_json)
        folders = client.list_subfolders("parent123")

        assert len(folders) == 2
        assert folders[0].id == "folder1"
        assert folders[0].name == "Subfolder 1"

    @patch("drive_sync.drive_client.build")
    @patch("drive_sync.drive_client.service_account.Credentials.from_service_account_info")
    def test_get_folder_name(
        self,
        mock_creds: MagicMock,
        mock_build: MagicMock,
        mock_credentials_json: str,
    ) -> None:
        """Test getting folder name by ID."""
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        mock_service.files().get().execute.return_value = {"name": "My Folder"}

        client = DriveClient(mock_credentials_json)
        name = client.get_folder_name("folder123")

        assert name == "My Folder"


class TestMimeTypes:
    """Tests for MIME type constants."""

    def test_google_doc_mime_type(self) -> None:
        """Test Google Docs MIME type."""
        assert GOOGLE_DOC_MIME_TYPE == "application/vnd.google-apps.document"

    def test_google_folder_mime_type(self) -> None:
        """Test Google Folder MIME type."""
        assert GOOGLE_FOLDER_MIME_TYPE == "application/vnd.google-apps.folder"

    def test_docx_mime_type(self) -> None:
        """Test DOCX MIME type."""
        assert DOCX_MIME_TYPE == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
