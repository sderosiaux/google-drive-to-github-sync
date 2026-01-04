"""Tests for the slugify module."""

import pytest

from drive_sync.slugify import slugify, slugify_filename, slugify_foldername


class TestSlugify:
    """Tests for the slugify function."""

    def test_simple_text(self) -> None:
        """Test slugifying simple text."""
        assert slugify("Hello World") == "hello-world"

    def test_mixed_case(self) -> None:
        """Test that output is lowercase."""
        assert slugify("MixedCASE") == "mixedcase"

    def test_special_characters(self) -> None:
        """Test handling of special characters."""
        assert slugify("Hello, World!") == "hello-world"

    def test_unicode(self) -> None:
        """Test handling of unicode characters."""
        assert slugify("Cafe Resume") == "cafe-resume"

    def test_numbers(self) -> None:
        """Test that numbers are preserved."""
        assert slugify("RFC 2024") == "rfc-2024"

    def test_multiple_spaces(self) -> None:
        """Test handling of multiple spaces."""
        assert slugify("Hello   World") == "hello-world"

    def test_leading_trailing_spaces(self) -> None:
        """Test handling of leading/trailing spaces."""
        assert slugify("  Hello World  ") == "hello-world"


class TestSlugifyFilename:
    """Tests for the slugify_filename function."""

    def test_simple_filename(self) -> None:
        """Test creating a simple filename."""
        assert slugify_filename("My Document") == "my-document.md"

    def test_complex_filename(self) -> None:
        """Test creating a complex filename."""
        assert slugify_filename("Kafka Proxy RFC") == "kafka-proxy-rfc.md"

    def test_filename_with_numbers(self) -> None:
        """Test filename with numbers."""
        assert slugify_filename("RFC 2024-001") == "rfc-2024-001.md"

    def test_filename_preserves_extension(self) -> None:
        """Test that .md extension is always added."""
        result = slugify_filename("Already.docx")
        assert result == "already-docx.md"


class TestSlugifyFoldername:
    """Tests for the slugify_foldername function."""

    def test_simple_foldername(self) -> None:
        """Test creating a simple folder name."""
        assert slugify_foldername("My Folder") == "my-folder"

    def test_foldername_with_special_chars(self) -> None:
        """Test folder name with special characters."""
        assert slugify_foldername("Product (2024)") == "product-2024"

    def test_foldername_no_extension(self) -> None:
        """Test that no extension is added to folder names."""
        result = slugify_foldername("Documents")
        assert "." not in result
        assert result == "documents"
