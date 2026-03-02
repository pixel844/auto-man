import pytest
from unittest.mock import MagicMock
from auto_man.mcp_server import McpServer


@pytest.fixture
def mock_model():
    """Mock LLM Engine."""
    return MagicMock()


@pytest.fixture
def mock_rag():
    """Mock RAG System."""
    return MagicMock()


def test_mcp_initialize(mock_model, mock_rag):
    """Verify MCP initialize request returns correct capabilities."""
    server = McpServer(mock_model, mock_rag)
    request = {"id": 1, "method": "initialize", "params": {}}
    response = server.handle_request(request)
    
    assert response["id"] == 1
    assert "capabilities" in response["result"]


def test_mcp_list_tools(mock_model, mock_rag):
    """Verify MCP tools/list request returns all available tools."""
    server = McpServer(mock_model, mock_rag)
    request = {"id": 2, "method": "tools/list", "params": {}}
    response = server.handle_request(request)
    
    tools = response["result"]["tools"]
    tool_names = [t["name"] for t in tools]
    assert "fetch_tree" in tool_names
    assert "generate_man" in tool_names


def test_mcp_invalid_method(mock_model, mock_rag):
    """Verify MCP error response for unknown methods."""
    server = McpServer(mock_model, mock_rag)
    request = {"id": 3, "method": "unknown_method", "params": {}}
    response = server.handle_request(request)
    
    assert "error" in response
    assert response["error"]["code"] == -32601
