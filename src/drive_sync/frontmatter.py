"""Frontmatter generator for Markdown files."""

import yaml


def generate_frontmatter(
    title: str,
    drive_id: str,
    modified_time: str,
) -> str:
    """Generate YAML frontmatter for a Markdown file.

    Args:
        title: Document title.
        drive_id: Google Drive document ID.
        modified_time: ISO 8601 timestamp of last modification.

    Returns:
        YAML frontmatter string including delimiters.
    """
    drive_url = f"https://docs.google.com/document/d/{drive_id}"

    data = {
        "title": title,
        "drive_id": drive_id,
        "drive_url": drive_url,
        "modified_time": modified_time,
        "source": "google-drive",
    }

    yaml_str = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{yaml_str}---"


def create_markdown_document(
    title: str,
    drive_id: str,
    modified_time: str,
    content: str,
) -> str:
    """Create a complete Markdown document with frontmatter.

    Args:
        title: Document title.
        drive_id: Google Drive document ID.
        modified_time: ISO 8601 timestamp of last modification.
        content: Markdown body content.

    Returns:
        Complete Markdown document with frontmatter.
    """
    frontmatter = generate_frontmatter(title, drive_id, modified_time)
    return f"{frontmatter}\n\n{content}\n"
