"""Tests for credential selection and safe automatic commits."""

import argparse
import logging
import subprocess
from unittest.mock import patch

import pytest
from google.auth.exceptions import DefaultCredentialsError

from drive_sync.cli import git_commit_changes, load_credentials, main


def test_credential_precedence(tmp_path, monkeypatch):
    credentials_file = tmp_path / "credentials.json"
    credentials_file.write_text("file credentials")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "environment credentials")
    args = argparse.Namespace(credentials_file=credentials_file, credentials="argument credentials")

    assert load_credentials(args) == "file credentials"
    args.credentials_file = None
    assert load_credentials(args) == "argument credentials"
    args.credentials = None
    assert load_credentials(args) == "environment credentials"
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    assert load_credentials(args) is None
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    assert load_credentials(args) is None


@pytest.mark.parametrize("command", [[], ["verify"]])
def test_commands_use_default_credentials(command, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    (tmp_path / ".drive-sync.yml").write_text(
        "sync:\n  - drive_folder_id: test\n    github_folder: docs\n"
    )
    monkeypatch.setattr("sys.argv", ["drive-sync", *command])

    with patch("drive_sync.cli.DriveClient") as client, patch(
        "drive_sync.cli.check_pandoc_available", return_value=True
    ):
        client.return_value.list_files.return_value = []
        client.return_value.list_subfolders.return_value = []
        assert main() == 0
        client.assert_called_once_with(None)


@pytest.mark.parametrize("command", [[], ["verify"]])
@pytest.mark.parametrize("failure", ["missing-file", "missing-adc"])
def test_credential_errors_fail_commands(command, failure, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
    (tmp_path / ".drive-sync.yml").write_text(
        "sync:\n  - drive_folder_id: test\n    github_folder: docs\n"
    )
    args = ["drive-sync", *command]
    if failure == "missing-file":
        args.extend(["--credentials-file", str(tmp_path / "missing.json")])
    monkeypatch.setattr("sys.argv", args)

    with patch("drive_sync.drive_client.google.auth.default") as default, patch(
        "drive_sync.cli.check_pandoc_available", return_value=True
    ), patch("drive_sync.drive_client.build") as build:
        default.side_effect = DefaultCredentialsError("No default credentials")
        assert main() == 1
        build.assert_not_called()
        if failure == "missing-file":
            default.assert_not_called()
        else:
            default.assert_called_once()


def test_auto_commit_excludes_auth_credentials(tmp_path):
    """Exercise real Git staging without relying on a consumer's .gitignore."""
    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=tmp_path, check=True, capture_output=True, text=True
        ).stdout

    git("init")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    git("config", "commit.gpgsign", "false")
    git("config", "core.hooksPath", "/dev/null")
    (tmp_path / "gha-creds-test.json").write_text("test credentials")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "gha-creds-nested.json").write_text("test credentials")
    (tmp_path / "docs" / "document.md").write_text("Exported document")

    assert git_commit_changes(tmp_path, logging.getLogger(__name__))
    assert git("ls-tree", "-r", "--name-only", "HEAD").splitlines() == ["docs/document.md"]
