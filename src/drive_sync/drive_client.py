"""Google Drive API client for fetching documents."""

import io
import json
from dataclasses import dataclass

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
GOOGLE_DOC_MIME_TYPE = "application/vnd.google-apps.document"
GOOGLE_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# Google Drive API page size (max 1000, 100 balances API calls vs memory)
DRIVE_API_PAGE_SIZE = 100


@dataclass
class DriveFile:
    """Represents a file from Google Drive."""

    id: str
    name: str
    mime_type: str
    modified_time: str


@dataclass
class DriveFolder:
    """Represents a folder from Google Drive."""

    id: str
    name: str


class DriveClient:
    """Client for interacting with Google Drive API."""

    def __init__(self, credentials_json: str):
        """Initialize the Drive client.

        Args:
            credentials_json: JSON string containing service account credentials.
        """
        creds_dict = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES
        )
        self._service = build("drive", "v3", credentials=credentials)

    def list_files(self, folder_id: str) -> list[DriveFile]:
        """List all Google Docs and uploaded .docx files in a folder.

        Args:
            folder_id: The ID of the Drive folder.

        Returns:
            List of DriveFile objects for Google Docs and .docx files in the folder.
        """
        query = (
            f"'{folder_id}' in parents and "
            f"(mimeType = '{GOOGLE_DOC_MIME_TYPE}' or mimeType = '{DOCX_MIME_TYPE}') and "
            f"trashed = false"
        )
        results = []
        page_token = None

        while True:
            response = (
                self._service.files()
                .list(
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                    pageToken=page_token,
                    pageSize=DRIVE_API_PAGE_SIZE,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )

            for file in response.get("files", []):
                results.append(
                    DriveFile(
                        id=file["id"],
                        name=file["name"],
                        mime_type=file["mimeType"],
                        modified_time=file["modifiedTime"],
                    )
                )

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return results

    def list_subfolders(self, folder_id: str) -> list[DriveFolder]:
        """List all subfolders in a folder.

        Args:
            folder_id: The ID of the Drive folder.

        Returns:
            List of DriveFolder objects for subfolders.
        """
        query = f"'{folder_id}' in parents and mimeType = '{GOOGLE_FOLDER_MIME_TYPE}' and trashed = false"
        results = []
        page_token = None

        while True:
            response = (
                self._service.files()
                .list(
                    q=query,
                    fields="nextPageToken, files(id, name)",
                    pageToken=page_token,
                    pageSize=DRIVE_API_PAGE_SIZE,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )

            for folder in response.get("files", []):
                results.append(
                    DriveFolder(
                        id=folder["id"],
                        name=folder["name"],
                    )
                )

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return results

    def export_as_docx(self, file_id: str) -> bytes:
        """Export a Google Doc as DOCX format.

        Args:
            file_id: The ID of the Google Doc.

        Returns:
            Bytes content of the DOCX file.
        """
        request = self._service.files().export(fileId=file_id, mimeType=DOCX_MIME_TYPE)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        return buffer.getvalue()

    def download_file(self, file_id: str) -> bytes:
        """Download an uploaded file (not a Google Workspace file).

        Args:
            file_id: The ID of the file.

        Returns:
            Bytes content of the file.
        """
        request = self._service.files().get_media(fileId=file_id, supportsAllDrives=True)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        return buffer.getvalue()

    def get_docx_content(self, file: "DriveFile") -> bytes:
        """Get DOCX content from either a Google Doc or uploaded .docx.

        Args:
            file: The DriveFile to get content from.

        Returns:
            Bytes content of the DOCX file.
        """
        if file.mime_type == GOOGLE_DOC_MIME_TYPE:
            return self.export_as_docx(file.id)
        else:
            return self.download_file(file.id)

    def get_folder_name(self, folder_id: str) -> str:
        """Get the name of a folder by its ID.

        Args:
            folder_id: The ID of the Drive folder.

        Returns:
            The folder name.
        """
        result = self._service.files().get(
            fileId=folder_id, fields="name", supportsAllDrives=True
        ).execute()
        return result["name"]
