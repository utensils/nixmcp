"""
Tests for MCP completion integration.

This module tests the integration of completion capabilities in the NixMCP server.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# Mock the FastMCP class since we don't want to actually use the real one in tests
class MockFastMCP:
    def __init__(self, name, version, description, capabilities=None, lifespan=None):
        self.name = name
        self.version = version
        self.description = description
        self.capabilities = capabilities or []
        self.lifespan = lifespan
        self.methods = {}

    def tool(self, name):
        def decorator(func):
            self.methods[name] = func
            return func

        return decorator


@pytest.mark.skip(reason="Completions are temporarily disabled until MCP SDK implementation is ready")
@pytest.mark.asyncio
async def test_mcp_completion_method():
    """Test the MCP completion/complete method."""
    # Create a MockFastMCP instance
    mcp = MockFastMCP(
        "NixMCP",
        version="0.1.0",
        description="NixOS Model Context Protocol Server",
        capabilities=["resources", "tools", "completions"],
    )

    # Create mock contexts outside the completion handler
    mock_nixos_context = MagicMock()
    mock_home_manager_context = MagicMock()

    # Mock handle_completion
    with patch("nixmcp.completions.handle_completion", new_callable=AsyncMock) as mock_handle:
        mock_handle.return_value = {"items": [{"label": "test", "value": "test"}]}

        # Register the completion method handler
        @mcp.tool("completion_complete")
        async def mcp_handle_completion(params: dict) -> dict:
            """Handle MCP completion requests."""
            # Pass the request to the mocked completion handler using the predefined mocks
            return await mock_handle(params, mock_nixos_context, mock_home_manager_context)

        # Prepare test params for resource completion
        params = {
            "ref": {"type": "ref/resource", "uri": "nixos://package/fi"},
            "argument": {"name": "test", "value": "test"},
        }

        # Call the method handler directly
        result = await mcp.methods["completion_complete"](params)

        # Verify handle_completion was called with correct parameters (use the same mock objects)
        mock_handle.assert_called_once_with(params, mock_nixos_context, mock_home_manager_context)
        assert result == {"items": [{"label": "test", "value": "test"}]}


@pytest.mark.skip(reason="Completions are temporarily disabled until MCP SDK implementation is ready")
@pytest.mark.asyncio
async def test_mcp_completion_capability():
    """Test that the MCP server has the completions capability."""
    # Create a MockFastMCP with completions capability
    mcp = MockFastMCP(
        "NixMCP",
        version="0.1.0",
        description="NixOS Model Context Protocol Server",
        capabilities=["resources", "tools", "completions"],
    )

    # Verify completions capability is included in the capabilities property
    assert "completions" in mcp.capabilities
