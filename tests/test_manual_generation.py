from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from auto_man.manual_generation import (
    build_manual_prompt,
    clean_roff_content,
    generate_manual,
    generate_manual_content,
)


class TestBuildManualPrompt:
    """Test building manual generation prompts."""

    def test_build_manual_prompt_qwen(self):
        """Test building prompt for Qwen model."""
        context = "Sample code context"
        result = build_manual_prompt("qwen2.5", context)

        assert result.startswith("<|im_start|>user\n")
        assert "You are a technical writer" in result
        assert "Sample code context" in result
        assert result.endswith("<|im_end|>\n<|im_start|>assistant\n")

    def test_build_manual_prompt_includes_template(self):
        """Test that prompt includes ROFF template."""
        context = "test context"
        result = build_manual_prompt("model", context)

        assert ".TH AUTO-MAN 1" in result
        assert ".SH NAME" in result
        assert ".SH SYNOPSIS" in result
        assert "ROFF TEMPLATE" in result


class TestCleanRoffContent:
    """Test ROFF content cleaning."""

    def test_clean_backspace_sequences(self):
        """Test removing backspace character sequences."""
        content = "Hello\x08\x08lo world"
        result = clean_roff_content(content)

        assert result == "Helllo world"

    def test_clean_literal_backslash_b(self):
        """Test removing literal \\b sequences."""
        content = "Some\\bcontent\\bhere"
        result = clean_roff_content(content)

        assert result == "Somecontenthere"

    def test_clean_mixed_sequences(self):
        """Test cleaning mixed backspace and \\b sequences."""
        content = "Test\x08\x08st\\bcontent\\b"
        result = clean_roff_content(content)

        assert result == "Tesstcontent"

    def test_clean_no_changes_needed(self):
        """Test content that doesn't need cleaning."""
        content = "Normal content without special chars"
        result = clean_roff_content(content)

        assert result == content


class TestGenerateManualContent:
    """Test manual content generation."""

    def test_generate_manual_content(self, fake_model, mock_rag):
        """Test generating manual content."""
        fake_model.responses = ["Generated", " ", "content"]

        with patch(
            "auto_man.manual_generation.build_manual_prompt", return_value="test prompt"
        ):
            content = generate_manual_content(
                fake_model, mock_rag, "https://example.com/repo"
            )

            assert content == "Generated content"
            # Should have called retrieve_context
            mock_rag.retrieve_context.assert_called_once()

    def test_generate_manual_content_with_callback(self, fake_model, mock_rag):
        """Test generating content with token callback."""
        fake_model.responses = ["Token1", "Token2"]

        tokens_received = []

        def callback(token):
            tokens_received.append(token)

        with patch(
            "auto_man.manual_generation.build_manual_prompt", return_value="test prompt"
        ):
            content = generate_manual_content(fake_model, mock_rag, "repo", callback)

            assert content == "Token1Token2"
            assert tokens_received == ["Token1", "Token2"]


class TestGenerateManual:
    """Test complete manual generation."""

    def test_generate_manual(self, tmp_path, fake_model, mock_rag):
        """Test generating and saving a manual file."""
        fake_model.responses = ["Manual", " ", "content"]
        output_path = tmp_path / "test.man"

        with patch(
            "auto_man.manual_generation.build_manual_prompt", return_value="test prompt"
        ):
            result_path = generate_manual(fake_model, mock_rag, "repo", output_path)

            assert result_path == output_path
            assert output_path.exists()

            content = output_path.read_text()
            assert content == "Manual content"

    def test_generate_manual_with_cleaning(self, tmp_path, fake_model, mock_rag):
        """Test that generated content is cleaned."""
        fake_model.responses = ["Manual\x08\x08ual", " content\\b"]
        output_path = tmp_path / "test.man"

        with patch(
            "auto_man.manual_generation.build_manual_prompt", return_value="test prompt"
        ):
            generate_manual(fake_model, mock_rag, "repo", output_path)

            content = output_path.read_text()
            assert content == "Manual content"  # Backspace and \b removed
