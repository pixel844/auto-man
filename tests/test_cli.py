from unittest.mock import MagicMock, patch
from pathlib import Path
from auto_man.cli import get_available_models, select_model

def test_get_available_models(mock_models_dir):
    """Verify available models are correctly identified."""
    # Setup test file structure
    model_name = "test-model"
    model_path = mock_models_dir / model_name
    model_path.mkdir()
    (model_path / "model.onnx").touch()
    
    available = get_available_models(mock_models_dir)
    assert len(available) == 1
    assert available[0].name == model_name

def test_select_model_single(mock_models_dir):
    """Verify single available model is automatically selected."""
    model_name = "test-model"
    model_path = mock_models_dir / model_name
    model_path.mkdir()
    (model_path / "model.onnx").touch()
    
    selected = select_model(mock_models_dir)
    assert selected.name == model_name

def test_select_model_default(mock_models_dir):
    """Verify default model is returned when none are available."""
    selected = select_model(mock_models_dir)
    assert selected.name == "qwen2.5-7b-instruct-onnx-qnn"
