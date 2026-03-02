from unittest.mock import Mock, patch

import pytest


class TestMcpServer:
    """Test the McpServer class."""

    def test_handle_initialize(self, mock_mcp_server):
        """Test the initialize method."""
        params = {"protocolVersion": "2024-11-05"}
        result = mock_mcp_server.handle_initialize(params)

        assert "protocolVersion" in result
        assert "capabilities" in result
        assert "serverInfo" in result
        assert result["serverInfo"]["name"] == "auto-man-python"

    def test_handle_list_tools(self, mock_mcp_server):
        """Test the list tools method."""
        result = mock_mcp_server.handle_list_tools(None)

        assert "tools" in result
        tools = result["tools"]
        tool_names = [tool["name"] for tool in tools]

        expected_tools = [
            "fetch_tree",
            "complete",
            "query_rag",
            "add_repo",
            "index_repo",
            "generate_man",
            "reset_conversation",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names

    def test_handle_request_initialize(self, mock_mcp_server):
        """Test handling initialize request."""
        request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}

        response = mock_mcp_server.handle_request(request)

        assert response["id"] == 1
        assert "result" in response
        assert "protocolVersion" in response["result"]

    def test_handle_request_unknown_method(self, mock_mcp_server):
        """Test handling unknown method."""
        request = {"jsonrpc": "2.0", "id": 1, "method": "unknown_method", "params": {}}

        response = mock_mcp_server.handle_request(request)

        assert response["id"] == 1
        assert "error" in response
        assert "Method not found" in response["error"]["message"]

    def test_complete_tool(self, mock_mcp_server, fake_model):
        """Test the complete tool."""
        # Setup fake model response
        fake_model.responses = ["Hello", " ", "world"]

        args = {"prompt": "Test prompt"}
        result = mock_mcp_server.complete(args)

        assert "content" in result
        assert len(result["content"]) == 1
        assert result["content"][0]["type"] == "text"
        assert "Hello world" in result["content"][0]["text"]
        assert "metadata" in result

    def test_complete_tool_missing_prompt(self, mock_mcp_server):
        """Test complete tool with missing prompt."""
        args = {}

        with pytest.raises(ValueError, match="Missing prompt"):
            mock_mcp_server.complete(args)

    def test_query_rag_tool(self, mock_mcp_server):
        """Test the query_rag tool."""
        # Mock the RAG retrieve_context method
        mock_mcp_server.rag.retrieve_context = Mock(return_value="test context")

        args = {"query": "test query"}
        result = mock_mcp_server.query_rag(args)

        assert "content" in result
        assert "metadata" in result
        # Should have called retrieve_context
        mock_mcp_server.rag.retrieve_context.assert_called_once_with("test query")

    def test_query_rag_tool_missing_query(self, mock_mcp_server):
        """Test query_rag tool with missing query."""
        args = {}

        with pytest.raises(ValueError, match="Missing query"):
            mock_mcp_server.query_rag(args)

    def test_add_repo_tool(self, mock_mcp_server):
        """Test the add_repo tool."""
        mock_mcp_server.rag.add_repo = Mock(return_value="repo-123")

        args = {"url": "/path/to/repo", "is_remote": False}
        result = mock_mcp_server.add_repo(args)

        assert "content" in result
        assert "repo-123" in result["content"][0]["text"]
        mock_mcp_server.rag.add_repo.assert_called_once_with("/path/to/repo", False)

    def test_index_repo_tool(self, mock_mcp_server):
        """Test the index_repo tool."""
        mock_mcp_server.rag.index_repo = Mock(return_value=True)

        args = {"id": "repo-123"}
        result = mock_mcp_server.index_repo(args)

        assert "content" in result
        assert "True" in result["content"][0]["text"]
        mock_mcp_server.rag.index_repo.assert_called_once_with("repo-123")

    def test_fetch_tree_tool(self, mock_mcp_server):
        """Test the fetch_tree tool."""
        with (
            patch("pathlib.Path") as mock_path_class,
            patch("os.walk") as mock_walk,
            patch("os.path.basename") as mock_basename,
        ):

            # Mock Path
            mock_path = Mock()
            mock_path_class.return_value = mock_path
            mock_path.exists.return_value = True

            mock_walk.return_value = [
                ("/root", ["dir1"], ["file1.txt", "file2.py"]),
                ("/root/dir1", [], ["file3.md"]),
            ]
            mock_basename.side_effect = lambda x: x.split("/")[-1]

            args = {"url": "/root"}
            result = mock_mcp_server.fetch_tree(args)

            assert "content" in result
            tree_text = result["content"][0]["text"]
            assert "file1.txt" in tree_text
            assert "file2.py" in tree_text

    def test_generate_man_tool(self, mock_mcp_server):
        """Test the generate_man tool."""
        args = {"repo_id": "repo-123"}

        # Mock RAG methods to avoid llmware initialization
        mock_mcp_server.rag.retrieve_context = Mock(return_value="test context")
        mock_mcp_server.rag._load_registry = Mock(return_value=[])

        with patch("llmware.configs.LLMWareConfig.setup_llmware_workspace"):
            result = mock_mcp_server.generate_man(args)

        assert "content" in result
        assert "Successfully generated" in result["content"][0]["text"]

    def test_reset_conversation_tool(self, mock_mcp_server):
        """Test the reset_conversation tool."""
        args = {}
        result = mock_mcp_server.reset_conversation(args)

        assert "content" in result
        assert "Conversation history reset" in result["content"][0]["text"]

    def test_handle_call_tool_complete(self, mock_mcp_server):
        """Test calling the complete tool via handle_call_tool."""
        fake_model = mock_mcp_server.model.model
        fake_model.responses = ["Test", " response"]

        params = {"name": "complete", "arguments": {"prompt": "test"}}

        result = mock_mcp_server.handle_call_tool(params)

        assert "content" in result
        assert "Test response" in result["content"][0]["text"]

    def test_handle_call_tool_unknown(self, mock_mcp_server):
        """Test calling an unknown tool."""
        params = {"name": "unknown_tool", "arguments": {}}

        with pytest.raises(ValueError, match="Unknown tool"):
            mock_mcp_server.handle_call_tool(params)
