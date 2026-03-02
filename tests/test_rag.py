import pytest
from pathlib import Path
from auto_man.rag import Rag, RepoEntry


def test_repo_entry_to_dict():
    """Verify RepoEntry conversion to dictionary."""
    entry = RepoEntry("test-id", "remote", "http://test.url")
    data = entry.to_dict()
    assert data["id"] == "test-id"
    assert data["type"] == "remote"
    assert data["url_or_path"] == "http://test.url"


def test_rag_initialization(mock_base_dir):
    """Verify Rag correctly initializes its cache and registry."""
    rag = Rag(mock_base_dir)
    assert rag.cache_dir.exists()
    assert rag.registry_path.name == "repos.json"


def test_rag_add_repo(mock_base_dir):
    """Verify repos are correctly added to the RAG registry."""
    rag = Rag(mock_base_dir)
    repo_id = rag.add_repo("http://test.url", True)
    assert len(repo_id) == 8
    
    registry = rag._load_registry()
    assert len(registry) == 1
    assert registry[0].url_or_path == "http://test.url"


def test_rag_cleanup(mock_base_dir):
    """Verify cache and registry are cleared during cleanup."""
    rag = Rag(mock_base_dir)
    rag.add_repo("http://test.url", True)
    
    # Mocking library object if needed (not strictly for this simple purge test)
    rag.cleanup()
    
    # Rag cleanup should purge .cache directory
    assert not (mock_base_dir / ".cache" / "repos.json").exists()
