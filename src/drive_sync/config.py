"""Configuration parser for .drive-sync.yml."""

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SyncEntry:
    """A single sync entry mapping a Drive folder to a GitHub folder."""

    drive_folder_id: str
    github_folder: str
    exclude_folders: list[str] = field(default_factory=list)
    exclude_files: list[str] = field(default_factory=list)

    def _matches_any_pattern(self, name: str, patterns: list[str]) -> bool:
        """Check if name matches any pattern (case-insensitive)."""
        name_lower = name.lower()
        return any(fnmatch.fnmatch(name_lower, p.lower()) for p in patterns)

    def is_folder_excluded(self, folder_name: str) -> bool:
        """Check if a folder should be excluded."""
        return self._matches_any_pattern(folder_name, self.exclude_folders)

    def is_file_excluded(self, file_name: str) -> bool:
        """Check if a file should be excluded."""
        return self._matches_any_pattern(file_name, self.exclude_files)


@dataclass
class Config:
    """Configuration for the Drive sync."""

    sync: list[SyncEntry]


def load_config(config_path: Path) -> Config:
    """Load configuration from a YAML file.

    Args:
        config_path: Path to the .drive-sync.yml file.

    Returns:
        Parsed configuration.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        ValueError: If the config file is invalid.
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError("Configuration file is empty")

    if "sync" not in data:
        raise ValueError("Configuration must contain a 'sync' key")

    if not isinstance(data["sync"], list):
        raise ValueError("'sync' must be a list")

    entries = []
    for i, entry in enumerate(data["sync"]):
        if not isinstance(entry, dict):
            raise ValueError(f"Sync entry {i} must be a mapping")

        if "drive_folder_id" not in entry:
            raise ValueError(f"Sync entry {i} missing 'drive_folder_id'")

        if "github_folder" not in entry:
            raise ValueError(f"Sync entry {i} missing 'github_folder'")

        exclude_folders = entry.get("exclude_folders", [])
        exclude_files = entry.get("exclude_files", [])

        if not isinstance(exclude_folders, list):
            raise ValueError(f"Sync entry {i} 'exclude_folders' must be a list")

        if not isinstance(exclude_files, list):
            raise ValueError(f"Sync entry {i} 'exclude_files' must be a list")

        entries.append(
            SyncEntry(
                drive_folder_id=entry["drive_folder_id"],
                github_folder=entry["github_folder"],
                exclude_folders=exclude_folders,
                exclude_files=exclude_files,
            )
        )

    return Config(sync=entries)
