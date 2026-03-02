from unittest.mock import Mock, patch

import pytest


class FakeModel:
    """Fake model for testing that implements the stream interface."""

    def __init__(self, responses=None, model_name="test-model"):
        self.responses = responses or ["Hello", " ", "world", "!"]
        self.model_name = model_name

    def stream(self, prompt):
        """Yield tokens from the fake responses."""
        for token in self.responses:
            yield token

    def generate(self, prompt, callback=None):
        """Generate content and call callback with each token."""
        full_response = ""
        for token in self.responses:
            full_response += token
            if callback:
                callback(token)
        return full_response


class FakeLibrary:
    """Fake Library class for testing."""

    def __init__(self):
        self.created_libraries = []
        self.loaded_libraries = []

    def create_new_library(self, name):
        self.created_libraries.append(name)
        return Mock()

    def load_library(self, name):
        self.loaded_libraries.append(name)
        return Mock()


class FakeQuery:
    """Fake Query class for testing."""

    def __init__(self, results=None):
        self.results = results or []

    def get_whole_library(self):
        return self.results


@pytest.fixture
def temp_project_root(tmp_path):
    """Create a temporary project root directory."""
    return tmp_path


@pytest.fixture
def fake_model():
    """Create a fake model for testing."""
    return FakeModel()


@pytest.fixture
def fake_library():
    """Create a fake library factory."""
    return FakeLibrary()


@pytest.fixture
def fake_query():
    """Create a fake query with sample results."""
    sample_results = [
        {
            "file_source": "main.py",
            "text_search": "def main():",
            "text": "def main():",
            "block_ID": 0,
        },
        {
            "file_source": "README.md",
            "text_search": "# Project Title",
            "text": "# Project Title",
            "block_ID": 1,
        },
    ]
    return FakeQuery(sample_results)


@pytest.fixture
def mock_rag(temp_project_root, fake_library):
    """Create a mock RAG instance with fake dependencies."""
    from unittest.mock import Mock

    from auto_man.rag import Rag

    # Create a temporary registry file
    registry_path = temp_project_root / "test_registry.json"

    rag = Rag(
        project_root=temp_project_root,
        registry_path=registry_path,
        library_factory=lambda: fake_library,
    )

    # Replace the library with a proper mock that supports Query operations
    mock_library = Mock()
    mock_library.library_name = "test_library"
    mock_library.account_name = "test_account"
    mock_library.get_embedding_status.return_value = []  # Empty list so len() works

    # Mock the Query.get_whole_library to return sample data
    with patch("llmware.retrieval.Query") as mock_query_class:
        mock_query_instance = Mock()
        mock_query_instance.get_whole_library.return_value = [
            {"file_source": "main.py", "text": "def main():", "block_ID": 0},
            {"file_source": "README.md", "text": "# Project", "block_ID": 1},
        ]
        mock_query_class.return_value = mock_query_instance
        rag.library = mock_library

    return rag


@pytest.fixture
def mock_llm_engine(fake_model):
    """Create a mock LLM engine with fake model."""
    from auto_man.llm_engine import LlmEngine

    return LlmEngine(model=fake_model)


@pytest.fixture
def mock_mcp_server(mock_llm_engine, mock_rag):
    """Create a mock MCP server with fake dependencies."""
    from auto_man.mcp_server import McpServer

    return McpServer(mock_llm_engine, mock_rag)
