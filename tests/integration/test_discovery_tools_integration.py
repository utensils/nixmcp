"""Integration tests for discovery tools in MCP-NixOS server."""

import pytest
import json
from unittest.mock import patch, MagicMock
import os

# Mark as integration tests
pytestmark = pytest.mark.integration

# Get patching helper for tests
from tests.fixtures.patch_helper import patch_elasticsearch_client, get_mocked_home_manager_client


@pytest.fixture
def mcp_server_with_discovery():
    """Create a FastMCP server instance with discovery tools registered."""
    from mcp.server.fastmcp import FastMCP
    from mcp_nixos.tools.discovery_tools import register_discovery_tools
    from mcp_nixos.contexts.nixos_context import NixOSContext
    from mcp_nixos.contexts.home_manager_context import HomeManagerContext
    from mcp_nixos.contexts.darwin.darwin_context import DarwinContext
    from mcp_nixos.tools.nixos_tools import register_nixos_tools
    from mcp_nixos.tools.home_manager_tools import register_home_manager_tools
    from mcp_nixos.tools.darwin.darwin_tools import register_darwin_tools
    
    # Create contexts with mocked clients
    with patch_elasticsearch_client() as es_mock:
        nixos_context = NixOSContext(es_client=es_mock)
        
        # Create a mock home manager client
        mock_hm_client = get_mocked_home_manager_client()
        home_manager_context = HomeManagerContext(hm_client=mock_hm_client)
        
        # Create a mock darwin context
        darwin_context = MagicMock(spec=DarwinContext)
        
        # Create the server with mocked contexts
        server = FastMCP(
            "Test MCP Server",
            version="0.0.1",
            description="Test server for discovery tools",
            capabilities=["resources", "tools"],
        )
        
        # Register all tools including discovery tools
        register_nixos_tools(server)
        register_home_manager_tools(server)
        register_darwin_tools(darwin_context, server)
        register_discovery_tools(server)
        
        yield server


@pytest.mark.asyncio
async def test_discover_tools_integration(mcp_server_with_discovery):
    """Test that the discover_tools tool works properly with the MCP server."""
    server = mcp_server_with_discovery
    
    # Create a tool call request
    request = {
        "type": "call",
        "tool": "discover_tools",
        "params": {}
    }
    
    # Process the request through the server
    response = await server.process_message(json.dumps(request))
    response_data = json.loads(response)
    
    # Check that the response is successful
    assert response_data["type"] == "result"
    assert "content" in response_data
    
    # Parse the content as JSON
    tools_list = response_data["content"]
    
    # Check that the tools list contains expected tools
    assert isinstance(tools_list, dict)
    assert "nixos_search" in tools_list
    assert "nixos_info" in tools_list
    assert "home_manager_search" in tools_list
    assert "discover_tools" in tools_list
    assert "get_tool_usage" in tools_list
    
    # Verify some tool descriptions
    assert "Search NixOS packages and options" in tools_list["nixos_search"]
    assert "List all available MCP tools" in tools_list["discover_tools"]


@pytest.mark.asyncio
async def test_get_tool_usage_integration(mcp_server_with_discovery):
    """Test that the get_tool_usage tool works properly with the MCP server."""
    server = mcp_server_with_discovery
    
    # Create a tool call request
    request = {
        "type": "call",
        "tool": "get_tool_usage",
        "params": {
            "tool_name": "nixos_search"
        }
    }
    
    # Process the request through the server
    response = await server.process_message(json.dumps(request))
    response_data = json.loads(response)
    
    # Check that the response is successful
    assert response_data["type"] == "result"
    assert "content" in response_data
    
    # Parse the content as JSON
    tool_usage = response_data["content"]
    
    # Check that the tool usage contains expected sections
    assert isinstance(tool_usage, dict)
    assert tool_usage["name"] == "nixos_search"
    assert "description" in tool_usage
    assert "parameters" in tool_usage
    assert "examples" in tool_usage
    assert "best_practices" in tool_usage
    
    # Check parameters section
    assert "query" in tool_usage["parameters"]
    assert tool_usage["parameters"]["query"]["required"] is True
    
    # Check examples section
    assert "Search packages" in tool_usage["examples"]
    assert "nixos_search" in tool_usage["examples"]["Search packages"]
    
    # Check best practices section
    assert "use_wildcards" in tool_usage["best_practices"]


@pytest.mark.asyncio
async def test_get_tool_usage_nonexistent_tool(mcp_server_with_discovery):
    """Test that get_tool_usage returns a helpful error for nonexistent tools."""
    server = mcp_server_with_discovery
    
    # Create a tool call request for a nonexistent tool
    request = {
        "type": "call",
        "tool": "get_tool_usage",
        "params": {
            "tool_name": "nonexistent_tool"
        }
    }
    
    # Process the request through the server
    response = await server.process_message(json.dumps(request))
    response_data = json.loads(response)
    
    # Check that the response is successful (the call succeeds but returns an error message)
    assert response_data["type"] == "result"
    assert "content" in response_data
    
    # Parse the content as JSON
    tool_usage = response_data["content"]
    
    # Check that the response contains an error and available tools list
    assert isinstance(tool_usage, dict)
    assert "error" in tool_usage
    assert "available_tools" in tool_usage
    assert "nonexistent_tool" in tool_usage["error"]
    assert isinstance(tool_usage["available_tools"], list)
    assert len(tool_usage["available_tools"]) > 0
    assert "nixos_search" in tool_usage["available_tools"]


@pytest.mark.asyncio
@pytest.mark.skipif(os.name == "nt", reason="Requires Linux/macOS")
async def test_prompt_includes_discovery_guidance(mcp_server_with_discovery):
    """Test that the prompt includes guidance about the discovery tools."""
    server = mcp_server_with_discovery
    
    # Get the prompt from the server (this is hacky but it works for testing)
    prompt_text = None
    for handler_name, handler in server.handlers.items():
        if handler_name == "prompt":
            prompt_text = handler()
            break
    
    # Check that the prompt contains guidance about discovery tools
    assert prompt_text is not None
    assert "Tool Discovery" in prompt_text
    assert "nixos_stats" in prompt_text
    assert "home_manager_stats" in prompt_text
    assert "darwin_stats" in prompt_text
    assert "understand available capabilities" in prompt_text.lower()