"""Slugify utility for file and folder names."""

from slugify import slugify as base_slugify


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug.

    Args:
        text: The text to slugify.

    Returns:
        A lowercase, hyphen-separated string.
    """
    return base_slugify(text, lowercase=True, separator="-")


def slugify_filename(name: str) -> str:
    """Convert a document name to a Markdown filename.

    Args:
        name: The document name from Drive.

    Returns:
        A slugified filename with .md extension.
    """
    return f"{slugify(name)}.md"


def slugify_foldername(name: str) -> str:
    """Convert a folder name to a slugified directory name.

    Args:
        name: The folder name from Drive.

    Returns:
        A slugified directory name.
    """
    return slugify(name)
