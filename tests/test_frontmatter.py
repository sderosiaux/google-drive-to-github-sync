"""Tests for the frontmatter module."""

import pytest
import yaml

from drive_sync.frontmatter import create_markdown_document, generate_frontmatter


class TestGenerateFrontmatter:
    """Tests for the generate_frontmatter function."""

    def test_basic_frontmatter(self) -> None:
        """Test generating basic frontmatter."""
        result = generate_frontmatter(
            title="Test Document",
            drive_id="abc123",
            modified_time="2026-01-03T18:22:11Z",
        )

        assert result.startswith("---\n")
        assert result.endswith("---")

    def test_frontmatter_contains_title(self) -> None:
        """Test that frontmatter contains title."""
        result = generate_frontmatter(
            title="My Document",
            drive_id="abc123",
            modified_time="2026-01-03T18:22:11Z",
        )

        assert "title: My Document" in result

    def test_frontmatter_contains_drive_id(self) -> None:
        """Test that frontmatter contains drive_id."""
        result = generate_frontmatter(
            title="Test",
            drive_id="xyz789",
            modified_time="2026-01-03T18:22:11Z",
        )

        assert "drive_id: xyz789" in result

    def test_frontmatter_contains_drive_url(self) -> None:
        """Test that frontmatter contains correct drive_url."""
        result = generate_frontmatter(
            title="Test",
            drive_id="abc123",
            modified_time="2026-01-03T18:22:11Z",
        )

        assert "drive_url: https://docs.google.com/document/d/abc123" in result

    def test_frontmatter_contains_modified_time(self) -> None:
        """Test that frontmatter contains modified_time."""
        result = generate_frontmatter(
            title="Test",
            drive_id="abc123",
            modified_time="2026-01-03T18:22:11Z",
        )

        assert "modified_time: '2026-01-03T18:22:11Z'" in result or "modified_time: 2026-01-03T18:22:11Z" in result

    def test_frontmatter_contains_source(self) -> None:
        """Test that frontmatter contains source."""
        result = generate_frontmatter(
            title="Test",
            drive_id="abc123",
            modified_time="2026-01-03T18:22:11Z",
        )

        assert "source: google-drive" in result

    def test_frontmatter_is_valid_yaml(self) -> None:
        """Test that frontmatter content is valid YAML."""
        result = generate_frontmatter(
            title="Test Document",
            drive_id="abc123",
            modified_time="2026-01-03T18:22:11Z",
        )

        yaml_content = result.strip("---").strip()
        parsed = yaml.safe_load(yaml_content)

        assert parsed["title"] == "Test Document"
        assert parsed["drive_id"] == "abc123"
        assert parsed["source"] == "google-drive"


class TestCreateMarkdownDocument:
    """Tests for the create_markdown_document function."""

    def test_complete_document(self) -> None:
        """Test creating a complete document."""
        result = create_markdown_document(
            title="Test Doc",
            drive_id="abc123",
            modified_time="2026-01-03T18:22:11Z",
            content="# Hello\n\nThis is content.",
        )

        assert result.startswith("---\n")
        assert "title: Test Doc" in result
        assert "# Hello" in result
        assert "This is content." in result
        assert result.endswith("\n")

    def test_document_structure(self) -> None:
        """Test the structure of the document."""
        result = create_markdown_document(
            title="Test",
            drive_id="abc",
            modified_time="2026-01-01T00:00:00Z",
            content="Body",
        )

        lines = result.split("\n")
        assert lines[0] == "---"

        second_delim_idx = None
        for i, line in enumerate(lines[1:], 1):
            if line == "---":
                second_delim_idx = i
                break

        assert second_delim_idx is not None
        assert "Body" in result[result.index("---", 4):]

    def test_empty_content(self) -> None:
        """Test document with empty content."""
        result = create_markdown_document(
            title="Empty Doc",
            drive_id="abc123",
            modified_time="2026-01-01T00:00:00Z",
            content="",
        )

        assert "---" in result
        assert "title: Empty Doc" in result

    def test_multiline_content(self) -> None:
        """Test document with multiline content."""
        content = """# Heading

Paragraph 1.

Paragraph 2.

- Item 1
- Item 2"""

        result = create_markdown_document(
            title="Multi",
            drive_id="abc",
            modified_time="2026-01-01T00:00:00Z",
            content=content,
        )

        assert "# Heading" in result
        assert "Paragraph 1." in result
        assert "- Item 1" in result
