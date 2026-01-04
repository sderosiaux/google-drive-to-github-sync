"""Sync orchestrator for Drive to GitHub mirroring."""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .config import SyncEntry
from .converter import convert_docx_to_markdown
from .drive_client import DriveClient, DriveFile, DriveFolder
from .frontmatter import create_markdown_document
from .slugify import slugify_filename, slugify_foldername

logger = logging.getLogger(__name__)


@dataclass
class SyncStats:
    """Statistics from a sync operation."""

    created: int = 0
    updated: int = 0
    deleted: int = 0
    unchanged: int = 0
    folders_created: int = 0
    errors: int = 0


def extract_modified_time(file_path: Path) -> str | None:
    """Extract modified_time from frontmatter of an existing markdown file.

    Args:
        file_path: Path to the markdown file.

    Returns:
        The modified_time string, or None if not found.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        if not content.startswith("---\n"):
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        data = yaml.safe_load(parts[1])
        if isinstance(data, dict):
            value = data.get("modified_time")
            if value is not None:
                # Return as-is if already a string
                if isinstance(value, str):
                    return value
                # YAML parses unquoted timestamps as datetime, format to ISO
                return value.isoformat().replace("+00:00", "Z")
    except Exception:
        pass
    return None


class Syncer:
    """Orchestrates the sync process from Drive to local filesystem."""

    def __init__(self, drive_client: DriveClient, base_path: Path, dry_run: bool = False):
        """Initialize the syncer.

        Args:
            drive_client: The Drive API client.
            base_path: Base path for writing synced files (repo root).
            dry_run: If True, only preview changes without writing files.
        """
        self._client = drive_client
        self._base_path = base_path
        self._dry_run = dry_run

    def sync_entry(self, entry: SyncEntry) -> SyncStats:
        """Sync a single configuration entry.

        Performs incremental sync:
        - Creates new files
        - Updates modified files
        - Deletes files no longer on Drive

        Args:
            entry: The sync entry to process.

        Returns:
            Statistics from the sync operation.
        """
        stats = SyncStats()
        target_path = self._base_path / entry.github_folder

        logger.info(f"Syncing Drive folder {entry.drive_folder_id} to {target_path}")

        if not self._dry_run:
            target_path.mkdir(parents=True, exist_ok=True)

        # Track all files we see from Drive (to detect deletions)
        seen_files: set[Path] = set()
        seen_folders: set[Path] = set()

        self._sync_folder_recursive(
            entry.drive_folder_id, target_path, entry, stats, seen_files, seen_folders
        )

        # Delete files that no longer exist on Drive
        self._cleanup_deleted(target_path, seen_files, seen_folders, stats)

        return stats

    def _sync_folder_recursive(
        self,
        folder_id: str,
        target_path: Path,
        entry: SyncEntry,
        stats: SyncStats,
        seen_files: set[Path],
        seen_folders: set[Path],
    ) -> None:
        """Recursively sync a Drive folder.

        Args:
            folder_id: The Drive folder ID to sync.
            target_path: The local path to write files to.
            entry: The sync entry with exclusion rules.
            stats: Statistics object to update.
            seen_files: Set to track which files exist on Drive.
            seen_folders: Set to track which folders exist on Drive.
        """
        files = self._client.list_files(folder_id)
        for file in files:
            if entry.is_file_excluded(file.name):
                logger.debug(f"Skipping excluded file: {file.name}")
                continue
            self._sync_file(file, target_path, stats, seen_files)

        subfolders = self._client.list_subfolders(folder_id)
        for subfolder in subfolders:
            if entry.is_folder_excluded(subfolder.name):
                logger.debug(f"Skipping excluded folder: {subfolder.name}")
                continue
            self._sync_subfolder(subfolder, target_path, entry, stats, seen_files, seen_folders)

    def _sync_file(
        self,
        file: DriveFile,
        target_path: Path,
        stats: SyncStats,
        seen_files: set[Path],
    ) -> None:
        """Sync a single document file (Google Doc or uploaded .docx).

        Only downloads and converts if the file is new or modified.

        Args:
            file: The Drive file to sync.
            target_path: The local path to write to.
            stats: Statistics object to update.
            seen_files: Set to track which files exist on Drive.
        """
        filename = slugify_filename(file.name)
        file_path = target_path / filename
        seen_files.add(file_path)

        # Check if file exists and is unchanged
        if file_path.exists():
            existing_modified_time = extract_modified_time(file_path)
            if existing_modified_time == file.modified_time:
                logger.debug(f"Unchanged: {file.name}")
                stats.unchanged += 1
                return

        # File is new or modified - download and convert
        is_update = file_path.exists()
        action = "Updating" if is_update else "Creating"
        prefix = "[DRY RUN] Would " if self._dry_run else ""
        logger.info(f"{prefix}{action.lower()}: {file.name} -> {filename}")

        if self._dry_run:
            if is_update:
                stats.updated += 1
            else:
                stats.created += 1
            return

        try:
            docx_content = self._client.get_docx_content(file)
            markdown_body = convert_docx_to_markdown(docx_content)
            markdown_doc = create_markdown_document(
                title=file.name,
                drive_id=file.id,
                modified_time=file.modified_time,
                content=markdown_body,
            )

            file_path.write_text(markdown_doc, encoding="utf-8")

            if is_update:
                stats.updated += 1
            else:
                stats.created += 1

            logger.info(f"Wrote: {file_path}")
        except Exception as e:
            stats.errors += 1
            logger.error(f"Failed to sync {file.name}: {e}")

    def _sync_subfolder(
        self,
        folder: DriveFolder,
        target_path: Path,
        entry: SyncEntry,
        stats: SyncStats,
        seen_files: set[Path],
        seen_folders: set[Path],
    ) -> None:
        """Sync a subfolder recursively.

        Args:
            folder: The Drive folder to sync.
            target_path: The parent local path.
            entry: The sync entry with exclusion rules.
            stats: Statistics object to update.
            seen_files: Set to track which files exist on Drive.
            seen_folders: Set to track which folders exist on Drive.
        """
        folder_name = slugify_foldername(folder.name)
        subfolder_path = target_path / folder_name
        seen_folders.add(subfolder_path)

        if not subfolder_path.exists():
            prefix = "[DRY RUN] Would create" if self._dry_run else "Creating"
            logger.info(f"{prefix} folder: {folder.name} -> {folder_name}")
            if not self._dry_run:
                subfolder_path.mkdir(parents=True, exist_ok=True)
            stats.folders_created += 1
        else:
            logger.debug(f"Folder exists: {folder_name}")

        self._sync_folder_recursive(
            folder.id, subfolder_path, entry, stats, seen_files, seen_folders
        )

    def _cleanup_deleted(
        self,
        target_path: Path,
        seen_files: set[Path],
        seen_folders: set[Path],
        stats: SyncStats,
    ) -> None:
        """Delete local files/folders that no longer exist on Drive.

        Args:
            target_path: The root sync folder.
            seen_files: Files that exist on Drive.
            seen_folders: Folders that exist on Drive.
            stats: Statistics object to update.
        """
        # Find all existing .md files
        for existing_file in target_path.rglob("*.md"):
            if existing_file not in seen_files:
                prefix = "[DRY RUN] Would delete" if self._dry_run else "Deleting"
                logger.info(f"{prefix} removed file: {existing_file}")
                if not self._dry_run:
                    existing_file.unlink()
                stats.deleted += 1

        # Find and remove empty directories (bottom-up)
        if not self._dry_run:
            for existing_dir in sorted(target_path.rglob("*"), reverse=True):
                if existing_dir.is_dir() and not any(existing_dir.iterdir()):
                    if existing_dir not in seen_folders and existing_dir != target_path:
                        logger.info(f"Deleting empty folder: {existing_dir}")
                        existing_dir.rmdir()
