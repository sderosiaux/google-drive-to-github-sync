"""Tests for the converter module."""

from unittest.mock import MagicMock, patch

import pytest

from drive_sync.converter import ConversionError, check_pandoc_available, convert_docx_to_markdown


class TestConvertDocxToMarkdown:
    """Tests for the convert_docx_to_markdown function."""

    @patch("drive_sync.converter.subprocess.run")
    def test_successful_conversion(self, mock_run: MagicMock) -> None:
        """Test successful conversion."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="# Hello World\n\nThis is content.",
            stderr="",
        )

        result = convert_docx_to_markdown(b"fake docx bytes")

        assert result == "# Hello World\n\nThis is content."
        mock_run.assert_called_once()

        call_args = mock_run.call_args
        assert "pandoc" in call_args[0][0]
        assert "-f" in call_args[0][0]
        assert "docx" in call_args[0][0]
        assert "-t" in call_args[0][0]
        assert "gfm" in call_args[0][0]

    @patch("drive_sync.converter.subprocess.run")
    def test_conversion_failure(self, mock_run: MagicMock) -> None:
        """Test that ConversionError is raised on failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: invalid input",
        )

        with pytest.raises(ConversionError, match="Pandoc conversion failed"):
            convert_docx_to_markdown(b"bad content")

    @patch("drive_sync.converter.subprocess.run")
    def test_output_is_stripped(self, mock_run: MagicMock) -> None:
        """Test that output is stripped of whitespace."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="  content with spaces  \n\n",
            stderr="",
        )

        result = convert_docx_to_markdown(b"fake")

        assert result == "content with spaces"

    @patch("drive_sync.converter.subprocess.run")
    def test_wrap_none_flag(self, mock_run: MagicMock) -> None:
        """Test that --wrap=none flag is used."""
        mock_run.return_value = MagicMock(returncode=0, stdout="content", stderr="")

        convert_docx_to_markdown(b"fake")

        call_args = mock_run.call_args[0][0]
        assert "--wrap=none" in call_args


class TestCheckPandocAvailable:
    """Tests for the check_pandoc_available function."""

    @patch("drive_sync.converter.subprocess.run")
    def test_pandoc_available(self, mock_run: MagicMock) -> None:
        """Test when Pandoc is available."""
        mock_run.return_value = MagicMock(returncode=0)

        assert check_pandoc_available() is True

    @patch("drive_sync.converter.subprocess.run")
    def test_pandoc_not_available(self, mock_run: MagicMock) -> None:
        """Test when Pandoc is not available."""
        mock_run.return_value = MagicMock(returncode=1)

        assert check_pandoc_available() is False

    @patch("drive_sync.converter.subprocess.run")
    def test_pandoc_not_found(self, mock_run: MagicMock) -> None:
        """Test when Pandoc binary is not found."""
        mock_run.side_effect = FileNotFoundError()

        assert check_pandoc_available() is False
