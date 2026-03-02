from unittest.mock import Mock

import pytest

from auto_man.llm_engine import GenerationStats, LlmEngine


class TestGenerationStats:
    """Test the GenerationStats data class."""

    def test_tps_calculation(self):
        """Test tokens per second calculation."""
        stats = GenerationStats(ttft=0.1, total_duration=2.0, total_tokens=100)
        assert stats.tps() == 50.0

    def test_tps_with_zero_duration(self):
        """Test TPS calculation with zero duration."""
        stats = GenerationStats(ttft=0.0, total_duration=0.0, total_tokens=10)
        assert stats.tps() == 0.0


class TestLlmEngine:
    """Test the LlmEngine class."""

    def test_init_with_injected_model(self, fake_model):
        """Test initialization with a pre-injected model."""
        engine = LlmEngine(model=fake_model)
        assert engine.model is fake_model
        assert engine.model_name == "test-model"

    def test_generate_with_fake_model(self, fake_model):
        """Test generation with a fake model."""
        engine = LlmEngine(model=fake_model)

        tokens_received = []

        def token_callback(token):
            tokens_received.append(token)

        stats = engine.generate("test prompt", token_callback)

        assert tokens_received == ["Hello", " ", "world", "!"]
        assert isinstance(stats, GenerationStats)
        assert stats.total_tokens == 4
        assert stats.total_duration >= 0

    def test_generate_with_empty_response(self):
        """Test generation with model that yields no tokens."""
        empty_model = Mock()
        empty_model.stream.return_value = []
        empty_model.model_name = "empty-model"

        engine = LlmEngine(model=empty_model)

        tokens_received = []

        def token_callback(token):
            tokens_received.append(token)

        stats = engine.generate("test prompt", token_callback)

        assert tokens_received == []
        assert stats.total_tokens == 0

    def test_generate_with_exception(self):
        """Test generation when model raises an exception."""
        error_model = Mock()
        error_model.stream.side_effect = Exception("Model error")
        error_model.model_name = "error-model"

        engine = LlmEngine(model=error_model)

        tokens_received = []

        def token_callback(token):
            tokens_received.append(token)

        # Should not raise exception, should handle it gracefully
        stats = engine.generate("test prompt", token_callback)

        assert tokens_received == []
        assert stats.total_tokens == 0

    def test_reset(self, fake_model):
        """Test the reset method."""
        engine = LlmEngine(model=fake_model)
        # reset should not raise any exceptions
        engine.reset()
