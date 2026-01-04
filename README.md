# Google Drive to GitHub Markdown Mirror

Sync Google Docs from Drive folders to GitHub as Markdown files with YAML frontmatter.

## Features

- Converts Google Docs and `.docx` files to Markdown via Pandoc
- Incremental sync (only downloads changed files)
- Preserves folder structure with slugified names
- YAML frontmatter with metadata (title, drive_id, modified_time)
- Exclusion patterns for files and folders
- Shared Drive (Team Drive) support
- Auto-commit option for CI/CD
- Dry-run mode to preview changes

## Prerequisites

- Python 3.10+
- [Pandoc](https://pandoc.org/installing.html) installed and in PATH
- Google Cloud service account with Drive API access

## Installation

```bash
pip install -e .
```

## Google Service Account Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the **Google Drive API**
4. Go to **IAM & Admin > Service Accounts**
5. Create a service account
6. Create a JSON key and download it
7. Share your Drive folder(s) with the service account email (e.g., `my-service@project.iam.gserviceaccount.com`)
   - **Viewer** access: can list files but NOT export Google Docs
   - **Contributor** access: required to export Google Docs to DOCX

## Configuration

Create a `.drive-sync.yml` file in your repository root:

```yaml
sync:
  - drive_folder_id: "1AbcDriveFolderId"
    github_folder: "docs/product"
    exclude_folders:
      - "Archive"
      - "*backup*"
    exclude_files:
      - "DRAFT*"
      - "*-old"

  - drive_folder_id: "9XyzDriveFolderId"
    github_folder: "docs/security"
```

### Finding Drive Folder IDs

Open the folder in Google Drive. The URL looks like:
```
https://drive.google.com/drive/folders/1qXYZ123abcDEF456
                                        └─────────────────┘
                                         This is the folder ID
```

## CLI Usage

```bash
# Basic sync
drive-sync --credentials-file path/to/credentials.json

# Using environment variable
export GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
drive-sync

# Preview changes without writing (dry-run)
drive-sync --dry-run

# Verbose output
drive-sync -v

# Sync and commit changes
drive-sync --commit

# Custom config file
drive-sync --config my-config.yml
```

### Commands

```bash
# Initialize a new config file interactively
drive-sync init

# Verify credentials and folder access
drive-sync verify
```

### All Options

| Option | Description |
|--------|-------------|
| `--config PATH` | Config file (default: `.drive-sync.yml`) |
| `--credentials JSON` | Service account JSON string |
| `--credentials-file PATH` | Path to service account JSON file |
| `--base-path PATH` | Output directory (default: current) |
| `--dry-run` | Preview changes without writing |
| `-v, --verbose` | Enable debug logging |
| `--commit` | Commit changes to git after sync |

## GitHub Actions

Add this workflow to `.github/workflows/sync.yml`:

```yaml
name: Sync Drive to GitHub

on:
  schedule:
    - cron: "0 */6 * * *"  # Every 6 hours
  workflow_dispatch:       # Manual trigger

permissions:
  contents: write

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Pandoc
        run: sudo apt-get update && sudo apt-get install -y pandoc

      - name: Install dependencies
        run: pip install -e .

      - name: Configure git
        run: |
          git config --local user.email "github-actions[bot]@users.noreply.github.com"
          git config --local user.name "github-actions[bot]"

      - name: Run sync
        env:
          GOOGLE_SERVICE_ACCOUNT_JSON: ${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}
        run: drive-sync --verbose --commit

      - name: Push changes
        run: git push || echo "Nothing to push"
```

### Setting up the Secret

1. Go to your GitHub repo > Settings > Secrets and variables > Actions
2. Create a new secret named `GOOGLE_SERVICE_ACCOUNT_JSON`
3. Paste the entire contents of your service account JSON file

## Output Format

Each synced file becomes a Markdown file with YAML frontmatter:

```markdown
---
title: "My Document Title"
drive_id: "1abc123DEF456"
modified_time: "2024-01-15T10:30:00Z"
---

# Document content here...
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=drive_sync
```

## License

MIT
