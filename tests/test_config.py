import sys
from pathlib import Path
from auto_man.config import BASE_DIR, MODELS_DIR, CACHE_DIR


def test_base_dir_resolution():
    """Verify base directory is correctly resolved relative to config.py."""
    # BASE_DIR should be the project root
    assert BASE_DIR.is_dir()
    assert (BASE_DIR / "src").exists()


def test_models_dir_path():
    """Verify models directory path is correctly constructed."""
    assert MODELS_DIR == BASE_DIR / "models"


def test_cache_dir_path():
    """Verify cache directory path is correctly constructed."""
    assert CACHE_DIR == BASE_DIR / ".cache"
