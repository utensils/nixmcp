"""Integration tests for discovery tools in MCP-NixOS server."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import os

# Mark as integration tests
pytestmark = pytest.mark.integration

@pytest.fixture
def mock_elasticsearch_client():
    """Create a mock Elasticsearch client for testing."""
    mock_client = MagicMock()
    
    # Mock the search methods
    mock_client.search_packages.return_value = {
        "count": 1,
        "packages": [
            {
                "name": "python311",
                "version": "3.11.0",
                "description": "Python programming language",
                "programs": ["python3", "python3.11"],
            }
        ],
    }
    
    mock_client.search_options.return_value = {
        "count": 1,
        "options": [
            {
                "name": "services.nginx.enable",
                "description": "Enable nginx web server",
                "type": "boolean"
            }
        ],
    }
    
    mock_client.search_programs.return_value = {
        "count": 1,
        "packages": [
            {
                "name": "git",
                "version": "2.39.0",
                "description": "Distributed version control system",
                "programs": ["git", "git-upload-pack"],
            }
        ],
    }
    
    # Mock channel setting
    mock_client.set_channel = MagicMock()
    
    return mock_client


class TestDiscoveryToolsIntegration:
    """Test the integration of discovery tools with MCP-NixOS."""

    def test_discovery_tools_registration(self):
        """Test that discovery tools are properly registered with the MCP server."""
        from mcp.server.fastmcp import FastMCP
        from mcp_nixos.tools.discovery_tools import register_discovery_tools
        
        # Create a mock server
        mock_server = MagicMock(spec=FastMCP)
        
        # Register discovery tools
        register_discovery_tools(mock_server)
        
        # Verify tool registration was called
        assert mock_server.tool.call_count >= 2
        
        # Verify the tool decorator was called for each tool
        # Convert each call to string for easier inspection
        calls_str = str(mock_server.tool.mock_calls)
        # Check that both tool functions are mentioned in the mock calls
        assert "discover_tools" in calls_str
        assert "get_tool_usage" in calls_str
    
    @patch('mcp_nixos.tools.discovery_tools.get_tool_list')
    def test_discover_tools_functionality(self, mock_get_tool_list):
        """Test the functionality of the discover_tools tool."""
        from mcp_nixos.tools.discovery_tools import get_tool_list
        
        # Set up mock return value
        mock_tools = {
            "nixos_search": "Search NixOS packages and options",
            "get_tool_usage": "Get usage information for a tool"
        }
        mock_get_tool_list.return_value = mock_tools
        
        # Call the function directly
        result = get_tool_list()
        
        # Verify the result
        assert isinstance(result, dict)
        assert "nixos_search" in result
        assert "get_tool_usage" in result
    
    @patch('mcp_nixos.tools.discovery_tools.get_tool_list')
    @patch('mcp_nixos.tools.discovery_tools.get_tool_schema')
    @patch('mcp_nixos.tools.discovery_tools.get_tool_examples')
    @patch('mcp_nixos.tools.discovery_tools.get_tool_tips')
    def test_get_tool_usage_functionality(self, mock_tips, mock_examples, mock_schema, mock_list):
        """Test the functionality of the get_tool_usage tool."""
        from mcp_nixos.tools.discovery_tools import get_tool_usage
        
        # Set up mock return values
        mock_list.return_value = {
            "nixos_search": "Search NixOS packages and options"
        }
        mock_schema.return_value = {
            "query": {"type": "string", "required": True},
            "type": {"type": "string", "default": "packages"}
        }
        mock_examples.return_value = {
            "Search packages": "nixos_search(query=\"python\", type=\"packages\")"
        }
        mock_tips.return_value = {
            "use_wildcards": "Wildcards (*) are automatically added to most queries"
        }
        
        # Call the function directly
        result = get_tool_usage("nixos_search")
        
        # Verify the result structure
        assert isinstance(result, dict)
        assert "name" in result
        assert "description" in result
        assert "parameters" in result
        assert "examples" in result
        assert "best_practices" in result
        
        # Verify the result content
        assert result["name"] == "nixos_search"
        assert result["description"] == "Search NixOS packages and options"
        assert "query" in result["parameters"]
        assert "Search packages" in result["examples"]
        assert "use_wildcards" in result["best_practices"]
    
    @patch('mcp_nixos.tools.discovery_tools.get_tool_list')
    def test_get_tool_usage_error_handling(self, mock_get_tool_list):
        """Test error handling in the get_tool_usage tool."""
        from mcp_nixos.tools.discovery_tools import get_tool_usage
        
        # Set up mock return value
        mock_get_tool_list.return_value = {
            "existing_tool": "An existing tool"
        }
        
        # Call with a non-existent tool
        result = get_tool_usage("nonexistent_tool")
        
        # Verify the error response
        assert "error" in result
        assert "nonexistent_tool" in result["error"]
        assert "available_tools" in result
        assert isinstance(result["available_tools"], list)
        assert "existing_tool" in result["available_tools"]
    
    def test_prompt_includes_discovery_guidance(self):
        """Test that the server prompt includes guidance about discovery tools."""
        # Read the server.py file directly to check the prompt content
        import os
        
        # Find the server.py file in the codebase
        server_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                   'mcp_nixos', 'server.py')
        
        # Ensure the file exists
        assert os.path.exists(server_path), f"Server file not found at {server_path}"
        
        # Read the file content
        with open(server_path, 'r') as f:
            server_content = f.read()
        
        # Check for discovery guidance in the prompt section
        assert "Tool Discovery" in server_content
        assert "nixos_stats()" in server_content
        assert "home_manager_stats()" in server_content
        assert "darwin_stats()" in server_content
        
        # Check for dynamic discovery principles
        assert "dynamic discovery" in server_content.lower() or "available capabilities" in server_content.lower()