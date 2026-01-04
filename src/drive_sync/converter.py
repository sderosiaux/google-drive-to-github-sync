"""DOCX to Markdown converter using Pandoc."""

import subprocess
import tempfile
from pathlib import Path


class ConversionError(Exception):
    """Raised when document conversion fails."""


def convert_docx_to_markdown(docx_content: bytes) -> str:
    """Convert DOCX content to GitHub Flavored Markdown.

    Args:
        docx_content: Bytes content of a DOCX file.

    Returns:
        Markdown string.

    Raises:
        ConversionError: If the conversion fails.
    """
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        f.write(docx_content)
        docx_path = Path(f.name)

    try:
        result = subprocess.run(
            [
                "pandoc",
                str(docx_path),
                "-f",
                "docx",
                "-t",
                "gfm",
                "--wrap=none",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise ConversionError(f"Pandoc conversion failed: {result.stderr}")

        return result.stdout.strip()
    finally:
        docx_path.unlink(missing_ok=True)


def check_pandoc_available() -> bool:
    """Check if Pandoc is available on the system.

    Returns:
        True if Pandoc is available, False otherwise.
    """
    try:
        result = subprocess.run(
            ["pandoc", "--version"],
            capture_output=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False
