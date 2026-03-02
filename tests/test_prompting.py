import pytest

from auto_man.prompting import PromptHandler, make_single_prompt


class TestPromptHandler:
    """Test the PromptHandler class."""

    def test_qwen_model_tags(self):
        """Test prompt tags for Qwen models."""
        handler = PromptHandler("qwen2.5-7b-instruct")
        assert handler.user_tag == "<|im_start|>user\n"
        assert handler.assistant_tag == "<|im_end|>\n<|im_start|>assistant\n"

    def test_non_qwen_model_tags(self):
        """Test prompt tags for non-Qwen models."""
        handler = PromptHandler("some-other-model")
        assert handler.user_tag == "<|user|>\n"
        assert handler.assistant_tag == "<|assistant|>\n"

    def test_default_model_tags(self):
        """Test default prompt tags when no model specified."""
        handler = PromptHandler("")
        assert handler.user_tag == "<|user|>\n"
        assert handler.assistant_tag == "<|assistant|>\n"

    def test_get_prompt_with_tag(self):
        """Test formatting prompt with tags."""
        handler = PromptHandler("qwen-model")
        prompt = "Hello world"
        formatted = handler.get_prompt_with_tag(prompt)

        expected = "<|im_start|>user\nHello world<|im_end|>\n<|im_start|>assistant\n"
        assert formatted == expected


class TestPromptHelpers:
    """Test prompt helper functions."""

    def test_make_single_prompt_qwen(self):
        """Test making single prompt for Qwen model."""
        result = make_single_prompt("qwen2.5", "Test prompt")

        assert result.startswith("<|im_start|>user\n")
        assert "Test prompt" in result
        assert result.endswith("<|im_end|>\n<|im_start|>assistant\n")

    def test_make_single_prompt_other(self):
        """Test making single prompt for other models."""
        result = make_single_prompt("other-model", "Test prompt")

        assert result.startswith("<|user|>\n")
        assert "Test prompt" in result
        assert result.endswith("<|assistant|>\n")
