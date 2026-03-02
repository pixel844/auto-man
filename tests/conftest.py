import pytest
from pathlib import Path

@pytest.fixture
def mock_base_dir(tmp_path):
    """Provide a temporary base directory for tests."""
    return tmp_path

@pytest.fixture
def mock_models_dir(mock_base_dir):
    """Provide a temporary models directory."""
    models_dir = mock_base_dir / "models"
    models_dir.mkdir()
    return models_dir

@pytest.fixture
def mock_repo_url():
    """Return a standard test repository URL."""
    return "https://github.com/example/test-repo.git"
