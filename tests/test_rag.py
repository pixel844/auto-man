from unittest.mock import Mock, patch

from auto_man.rag import Rag, RepoEntry


class TestRepoEntry:
    """Test the RepoEntry data class."""

    def test_to_dict(self):
        """Test serialization to dict."""
        entry = RepoEntry(
            id="test-123",
            type="local",
            url_or_path="/path/to/repo",
            last_indexed="2023-01-01T00:00:00",
            status="indexed",
        )

        expected = {
            "id": "test-123",
            "type": "local",
            "url_or_path": "/path/to/repo",
            "last_indexed": "2023-01-01T00:00:00",
            "status": "indexed",
        }

        assert entry.to_dict() == expected

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "id": "test-123",
            "type": "remote",
            "url_or_path": "https://github.com/user/repo",
            "last_indexed": None,
            "status": "pending",
        }

        entry = RepoEntry.from_dict(data)

        assert entry.id == "test-123"
        assert entry.type == "remote"
        assert entry.url_or_path == "https://github.com/user/repo"
        assert entry.last_indexed is None
        assert entry.status == "pending"


class TestRag:
    """Test the Rag class."""

    def test_init_with_custom_registry_path(self, temp_project_root):
        """Test initialization with custom registry path."""
        custom_path = temp_project_root / "custom_registry.json"
        rag = Rag(temp_project_root, registry_path=custom_path)

        assert rag.registry_path == custom_path

    def test_load_registry_empty(self, mock_rag):
        """Test loading empty registry."""
        registry = mock_rag._load_registry()
        assert registry == []

    def test_save_and_load_registry(self, mock_rag):
        """Test saving and loading registry."""
        entries = [
            RepoEntry("id1", "local", "/path1"),
            RepoEntry("id2", "remote", "https://github.com/user/repo"),
        ]

        mock_rag._save_registry(entries)
        loaded = mock_rag._load_registry()

        assert len(loaded) == 2
        assert loaded[0].id == "id1"
        assert loaded[1].url_or_path == "https://github.com/user/repo"

    def test_add_repo(self, mock_rag):
        """Test adding a repository."""
        repo_id = mock_rag.add_repo("/path/to/repo", is_remote=False)

        assert repo_id is not None
        registry = mock_rag._load_registry()
        assert len(registry) == 1
        assert registry[0].url_or_path == "/path/to/repo"
        assert registry[0].type == "local"

    def test_chunk_text(self, mock_rag):
        """Test text chunking functionality."""
        text = "This is a test text that should be chunked into smaller pieces."
        chunks = mock_rag._chunk_text(text, max_chars=20, overlap=5)

        assert len(chunks) > 1
        # First chunk should be at most max_chars
        assert len(chunks[0]) <= 20
        # Chunks should overlap
        if len(chunks) > 1:
            # Check that there's overlap between chunks
            assert chunks[0][-5:] == chunks[1][:5] or chunks[0].endswith(" ")

    def test_chunk_text_short(self, mock_rag):
        """Test chunking with text shorter than max_chars."""
        text = "Short text"
        chunks = mock_rag._chunk_text(text, max_chars=50, overlap=5)

        assert len(chunks) == 1
        assert chunks[0] == text

    @patch("tempfile.TemporaryDirectory")
    @patch("subprocess.run")
    def test_index_repo_remote(self, mock_subprocess, mock_temp_dir, mock_rag):
        """Test indexing a remote repository."""
        # Mock the temporary directory
        mock_temp_dir.return_value.__enter__.return_value = "/tmp/test"
        mock_temp_dir.return_value.__exit__.return_value = None
        mock_subprocess.return_value.returncode = 0

        # Mock the library
        mock_library = Mock()
        mock_rag.library = mock_library

        # Create a fake repo entry
        repo_id = mock_rag.add_repo("https://github.com/user/repo.git", is_remote=True)

        # Mock file scanning - create some fake files
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.glob", return_value=[]),
            patch("pathlib.Path.iterdir", return_value=[]),
            patch("auto_man.rag.Library") as mock_lib_class,
        ):

            mock_lib_instance = Mock()
            mock_lib_class.return_value.load_library.return_value = mock_lib_instance

            result = mock_rag.index_repo(repo_id)

            # Should have attempted to clone and index
            assert result is True
            mock_subprocess.assert_called_once()

    def test_retrieve_context_with_fake_query(self, mock_rag, fake_query):
        """Test context retrieval with fake query results."""
        with patch("auto_man.rag.Query", return_value=fake_query):
            context = mock_rag.retrieve_context("test query")

            assert "main.py" in context
            assert "README.md" in context
            assert "FILE: main.py" in context

    def test_retrieve_context_priority_files(self, mock_rag):
        """Test that priority files are included first."""
        sample_results = [
            {
                "file_source": "main.py",
                "text_search": "main content",
                "text": "main content",
                "block_ID": 0,
            },
            {
                "file_source": "requirements.txt",
                "text_search": "deps",
                "text": "deps",
                "block_ID": 1,
            },
            {
                "file_source": "other.py",
                "text_search": "other",
                "text": "other",
                "block_ID": 2,
            },
        ]

        with patch("auto_man.rag.Query") as mock_query_class:
            mock_query = Mock()
            mock_query.get_whole_library.return_value = sample_results
            mock_query_class.return_value = mock_query

            context = mock_rag.retrieve_context("test")

            # Priority files should come first
            main_pos = context.find("FILE: main.py")
            req_pos = context.find("FILE: requirements.txt")
            other_pos = context.find("FILE: other.py")

            assert main_pos < req_pos  # main.py before requirements.txt
            assert req_pos < other_pos  # requirements.txt before other.py

    def test_cleanup(self, mock_rag):
        """Test cleanup functionality."""
        mock_library = Mock()
        mock_rag.library = mock_library
        mock_rag.library_name = "test_lib"

        with patch("shutil.rmtree") as mock_rmtree:
            mock_rag.cleanup()

            assert mock_rag.library is None
            assert mock_rag.library_name is None
            # Should attempt to delete the library
            mock_library.delete_library.assert_called_once()
            # Should attempt to remove cache directory
            mock_rmtree.assert_called_once()
            call_args = mock_rmtree.call_args
            assert call_args[0][0] == mock_rag.cache_dir
