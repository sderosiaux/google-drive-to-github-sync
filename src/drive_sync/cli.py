"""CLI entry point for the Drive sync tool."""

import argparse
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .config import load_config
from .converter import check_pandoc_available
from .drive_client import DriveClient
from .sync import Syncer

EXAMPLE_CONFIG = """\
sync:
  - drive_folder_id: "YOUR_DRIVE_FOLDER_ID"
    github_folder: "docs"
    # Optional: exclude folders/files using glob patterns
    # exclude_folders:
    #   - "Archive"
    # exclude_files:
    #   - "DRAFT*"
"""


def load_credentials(args: argparse.Namespace, logger: logging.Logger) -> str | None:
    """Load credentials from file, argument, or environment.

    Args:
        args: Parsed CLI arguments.
        logger: Logger instance.

    Returns:
        Credentials JSON string, or None if not found.
    """
    # Priority: --credentials-file > --credentials > env var
    if args.credentials_file:
        try:
            return args.credentials_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.error(f"Credentials file not found: {args.credentials_file}")
            return None
        except PermissionError:
            logger.error(f"Cannot read credentials file: {args.credentials_file}")
            return None

    if args.credentials:
        return args.credentials

    env_creds = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if env_creds:
        return env_creds

    logger.error(
        "No credentials provided. Use --credentials-file, --credentials, "
        "or set GOOGLE_SERVICE_ACCOUNT_JSON environment variable"
    )
    return None


def git_commit_changes(base_path: Path, logger: logging.Logger) -> bool:
    """Commit any changes to git if there are any.

    Args:
        base_path: The repository base path.
        logger: Logger instance.

    Returns:
        True if changes were committed, False otherwise.
    """
    try:
        subprocess.run(
            ["git", "add", "-A"],
            cwd=base_path,
            check=True,
            capture_output=True,
        )

        result = subprocess.run(
            ["git", "diff", "--staged", "--quiet"],
            cwd=base_path,
            capture_output=True,
        )

        if result.returncode == 0:
            logger.info("No changes to commit")
            return False

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        commit_msg = f"Sync: Update from Google Drive ({timestamp})"

        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=base_path,
            check=True,
            capture_output=True,
        )

        logger.info(f"Committed changes: {commit_msg}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Git operation failed: {e.stderr.decode() if e.stderr else e}")
        return False
    except FileNotFoundError:
        logger.error("Git is not installed or not in PATH")
        return False


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the CLI.

    Args:
        verbose: If True, enable DEBUG level logging.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize a new configuration file.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code.
    """
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    config_path = args.config
    if config_path.exists():
        logger.error(f"Configuration file already exists: {config_path}")
        logger.info("Edit it directly or delete it to create a new one")
        return 1

    config_path.write_text(EXAMPLE_CONFIG, encoding="utf-8")
    logger.info(f"Created configuration file: {config_path}")
    logger.info("Edit it with your Drive folder IDs and run 'drive-sync' to sync")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify credentials and folder access.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code.
    """
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    credentials = load_credentials(args, logger)
    if not credentials:
        return 1

    try:
        client = DriveClient(credentials)
        logger.info("Credentials valid")
    except Exception as e:
        logger.error(f"Invalid credentials: {e}")
        return 1

    try:
        config = load_config(args.config)
    except FileNotFoundError:
        logger.warning(f"No config file found at {args.config}")
        logger.info("Credentials are valid. Create a config file to verify folder access.")
        return 0
    except ValueError as e:
        logger.error(f"Invalid config: {e}")
        return 1

    all_ok = True
    for entry in config.sync:
        try:
            folder_name = client.get_folder_name(entry.drive_folder_id)
            files = client.list_files(entry.drive_folder_id)
            subfolders = client.list_subfolders(entry.drive_folder_id)
            logger.info(
                f"[OK] {entry.drive_folder_id} -> {entry.github_folder} "
                f"('{folder_name}': {len(files)} files, {len(subfolders)} subfolders)"
            )
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                logger.error(
                    f"[FAIL] {entry.drive_folder_id}: Folder not found. "
                    "Check the ID or share the folder with the service account."
                )
            elif "403" in error_msg:
                logger.error(
                    f"[FAIL] {entry.drive_folder_id}: Access denied. "
                    "Share the folder with the service account (Contributor access for Google Docs)."
                )
            else:
                logger.error(f"[FAIL] {entry.drive_folder_id}: {e}")
            all_ok = False

    return 0 if all_ok else 1


def cmd_sync(args: argparse.Namespace) -> int:
    """Run the sync operation.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code.
    """
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    if args.dry_run:
        logger.info("DRY RUN - no files will be written")

    if not check_pandoc_available():
        logger.error("Pandoc is not installed or not in PATH")
        return 1

    credentials = load_credentials(args, logger)
    if not credentials:
        return 1

    try:
        config = load_config(args.config)
        logger.info(f"Loaded configuration with {len(config.sync)} sync entries")
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Configuration error: {e}")
        return 1

    try:
        client = DriveClient(credentials)
    except Exception as e:
        logger.error(f"Failed to initialize Drive client: {e}")
        return 1

    syncer = Syncer(client, args.base_path, dry_run=args.dry_run)

    total_created = 0
    total_updated = 0
    total_deleted = 0
    total_unchanged = 0
    total_errors = 0

    for entry in config.sync:
        try:
            stats = syncer.sync_entry(entry)
            total_created += stats.created
            total_updated += stats.updated
            total_deleted += stats.deleted
            total_unchanged += stats.unchanged
            total_errors += stats.errors
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                logger.error(
                    f"Folder {entry.drive_folder_id} not found. "
                    "Check the ID or share the folder with the service account."
                )
            elif "403" in error_msg and "cannotExportFile" in error_msg:
                logger.error(
                    f"Cannot export files from {entry.drive_folder_id}. "
                    "The service account needs Contributor access (not just Viewer)."
                )
            elif "403" in error_msg:
                logger.error(
                    f"Access denied to {entry.drive_folder_id}. "
                    "Share the folder with the service account."
                )
            else:
                logger.error(f"Failed to sync {entry.github_folder}: {e}")
            total_errors += 1

    action = "Would sync" if args.dry_run else "Sync complete"
    logger.info(
        f"{action}: {total_created} created, {total_updated} updated, "
        f"{total_deleted} deleted, {total_unchanged} unchanged, {total_errors} errors"
    )

    if args.commit and total_errors == 0 and not args.dry_run:
        git_commit_changes(args.base_path, logger)

    return 0 if total_errors == 0 else 1


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to a parser."""
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(".drive-sync.yml"),
        help="Path to configuration file (default: .drive-sync.yml)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )


def add_credentials_args(parser: argparse.ArgumentParser) -> None:
    """Add credentials arguments to a parser."""
    parser.add_argument(
        "--credentials",
        type=str,
        default=None,
        help="Google service account JSON string",
    )
    parser.add_argument(
        "--credentials-file",
        type=Path,
        default=None,
        help="Path to service account JSON file",
    )


def main() -> int:
    """Main entry point for the CLI.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    parser = argparse.ArgumentParser(
        description="Sync Google Drive folders to GitHub as Markdown",
    )
    subparsers = parser.add_subparsers(dest="command")

    # Init command
    init_parser = subparsers.add_parser("init", help="Create a new configuration file")
    add_common_args(init_parser)

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify credentials and folder access")
    add_common_args(verify_parser)
    add_credentials_args(verify_parser)

    # Sync is the default (no subcommand needed)
    # Add sync args directly to main parser
    add_common_args(parser)
    add_credentials_args(parser)
    parser.add_argument(
        "--base-path",
        type=Path,
        default=Path.cwd(),
        help="Base path for output (default: current directory)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Commit changes to git after sync",
    )

    args = parser.parse_args()

    try:
        if args.command == "init":
            return cmd_init(args)
        elif args.command == "verify":
            return cmd_verify(args)
        else:
            return cmd_sync(args)
    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(130)
