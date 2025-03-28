"""
Tests for MCP completion functionality.

This module tests the completion handler and specific completion implementations
for NixOS and Home Manager resources and tools.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nixmcp.completions import (
    handle_completion,
    complete_resource_uri,
    complete_tool_argument,
)

from nixmcp.completions.utils import create_completion_item


# Test basic completion item creation
@pytest.mark.skip(reason="Skipped until MCP SDK implements completion/complete support")
def test_create_completion_item():
    """Test the create_completion_item utility function."""
    # Test with all fields
    item = create_completion_item("label", "value", "detail")
    assert item == {"label": "label", "value": "value", "detail": "detail"}

    # Test without detail
    item = create_completion_item("label", "value")
    assert item == {"label": "label", "value": "value"}


# Test main completion handler
@pytest.mark.skip(reason="Skipped until MCP SDK implements completion/complete support")
@pytest.mark.asyncio
async def test_handle_completion_resource():
    """Test the handle_completion function with resource references."""
    # Mock the contexts and dependencies
    nixos_context = MagicMock()
    home_manager_context = MagicMock()

    # Mock resource URI completion
    with patch("nixmcp.completions.complete_resource_uri", new_callable=AsyncMock) as mock_resource:
        mock_resource.return_value = {"items": [{"label": "test", "value": "test"}]}

        # Test resource reference
        params = {
            "ref": {"type": "ref/resource", "uri": "nixos://package/test"},
            "argument": {"name": "test", "value": "test"},
        }

        result = await handle_completion(params, nixos_context, home_manager_context)

        # Verify the resource URI completion was called
        mock_resource.assert_called_once_with("nixos://package/test", nixos_context, home_manager_context)
        assert result == {"items": [{"label": "test", "value": "test"}]}


@pytest.mark.skip(reason="Skipped until MCP SDK implements completion/complete support")
@pytest.mark.asyncio
async def test_handle_completion_tool():
    """Test the handle_completion function with tool references."""
    # Mock the contexts and dependencies
    nixos_context = MagicMock()
    home_manager_context = MagicMock()

    # Mock tool argument completion
    with patch("nixmcp.completions.complete_tool_argument", new_callable=AsyncMock) as mock_tool:
        mock_tool.return_value = {"items": [{"label": "test", "value": "test"}]}

        # Test tool reference
        params = {"ref": {"type": "ref/tool", "name": "nixos_search"}, "argument": {"name": "query", "value": "test"}}

        result = await handle_completion(params, nixos_context, home_manager_context)

        # Verify the tool argument completion was called
        mock_tool.assert_called_once_with("nixos_search", "query", "test", nixos_context, home_manager_context)
        assert result == {"items": [{"label": "test", "value": "test"}]}


@pytest.mark.skip(reason="Skipped until MCP SDK implements completion/complete support")
@pytest.mark.asyncio
async def test_handle_completion_prompt():
    """Test the handle_completion function with prompt references."""
    # Mock the contexts and dependencies
    nixos_context = MagicMock()
    home_manager_context = MagicMock()

    # Mock prompt argument completion
    with patch("nixmcp.completions.complete_prompt_argument", new_callable=AsyncMock) as mock_prompt:
        mock_prompt.return_value = {"items": [{"label": "test", "value": "test"}]}

        # Test prompt reference
        params = {"ref": {"type": "ref/prompt", "name": "test_prompt"}, "argument": {"name": "arg", "value": "test"}}

        result = await handle_completion(params, nixos_context, home_manager_context)

        # Verify the prompt argument completion was called
        mock_prompt.assert_called_once_with("test_prompt", "arg", "test", nixos_context, home_manager_context)
        assert result == {"items": [{"label": "test", "value": "test"}]}


@pytest.mark.skip(reason="Skipped until MCP SDK implements completion/complete support")
@pytest.mark.asyncio
async def test_handle_completion_unknown_type():
    """Test the handle_completion function with unknown reference type."""
    # Mock the contexts and dependencies
    nixos_context = MagicMock()
    home_manager_context = MagicMock()

    # Test unknown reference type
    params = {"ref": {"type": "ref/unknown"}, "argument": {"name": "test", "value": "test"}}

    result = await handle_completion(params, nixos_context, home_manager_context)

    # Verify empty results are returned
    assert result == {"items": []}


@pytest.mark.skip(reason="Skipped until MCP SDK implements completion/complete support")
@pytest.mark.asyncio
async def test_handle_completion_error():
    """Test the handle_completion function handles errors gracefully."""
    # Mock the contexts and dependencies
    nixos_context = MagicMock()
    home_manager_context = MagicMock()

    # Mock resource URI completion to raise an exception
    with patch("nixmcp.completions.complete_resource_uri", new_callable=AsyncMock) as mock_resource:
        mock_resource.side_effect = Exception("Test error")

        # Test resource reference that will raise an error
        params = {
            "ref": {"type": "ref/resource", "uri": "nixos://package/test"},
            "argument": {"name": "test", "value": "test"},
        }

        result = await handle_completion(params, nixos_context, home_manager_context)

        # Verify empty results are returned on error
        assert result == {"items": []}


# Test resource URI completion
@pytest.mark.skip(reason="Skipped until MCP SDK implements completion/complete support")
@pytest.mark.asyncio
async def test_complete_resource_uri_nixos_package():
    """Test resource URI completion for NixOS packages."""
    # Mock the contexts and dependencies
    nixos_context = MagicMock()
    home_manager_context = MagicMock()
    es_client = MagicMock()
    nixos_context.get_es_client.return_value = es_client

    # Test NixOS package URI
    uri = "nixos://package/test"

    # Mock the actual implementation function that gets called
    with patch("nixmcp.completions.complete_nixos_package_name", new_callable=AsyncMock) as mock_package:
        mock_package.return_value = {"items": [{"label": "test", "value": "test"}]}

        result = await complete_resource_uri(uri, nixos_context, home_manager_context)

        # Verify package completion was called with correct arguments
        mock_package.assert_called_once_with("test", es_client)
        assert result == {"items": [{"label": "test", "value": "test"}]}


@pytest.mark.skip(reason="Skipped until MCP SDK implements completion/complete support")
@pytest.mark.asyncio
async def test_complete_resource_uri_home_manager_option():
    """Test resource URI completion for Home Manager options."""
    # Mock the contexts and dependencies
    nixos_context = MagicMock()
    home_manager_context = MagicMock()
    hm_client = MagicMock()
    home_manager_context.get_home_manager_client.return_value = hm_client

    # Test Home Manager option URI
    uri = "home-manager://option/test"

    # Mock the actual implementation function that gets called
    with patch("nixmcp.completions.complete_home_manager_option_name", new_callable=AsyncMock) as mock_option:
        mock_option.return_value = {"items": [{"label": "test", "value": "test"}]}

        result = await complete_resource_uri(uri, nixos_context, home_manager_context)

        # Verify option completion was called with correct arguments
        mock_option.assert_called_once_with("test", hm_client)
        assert result == {"items": [{"label": "test", "value": "test"}]}


@pytest.mark.skip(reason="Skipped until MCP SDK implements completion/complete support")
@pytest.mark.asyncio
async def test_complete_resource_uri_root_paths():
    """Test resource URI completion for root resource paths."""
    # Mock the contexts and dependencies
    nixos_context = MagicMock()
    home_manager_context = MagicMock()

    # Test NixOS root URI
    uri = "nixos://"

    result = await complete_resource_uri(uri, nixos_context, home_manager_context)

    # Verify root path completions are returned
    assert isinstance(result, dict)
    assert "items" in result
    assert len(result["items"]) > 0
    assert all(isinstance(item, dict) for item in result["items"])
    assert all("label" in item and "value" in item for item in result["items"])


# Test tool argument completion
@pytest.mark.skip(reason="Skipped until MCP SDK implements completion/complete support")
@pytest.mark.asyncio
async def test_complete_tool_argument_nixos_search():
    """Test tool argument completion for nixos_search tool."""
    # Mock the contexts and dependencies
    nixos_context = MagicMock()
    home_manager_context = MagicMock()

    # Test nixos_search tool arguments
    tool_name = "nixos_search"
    arg_name = "query"
    arg_value = "test"

    # Mock the actual implementation function that gets called
    with patch("nixmcp.completions.complete_nixos_search_arguments", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = {"items": [{"label": "test", "value": "test"}]}

        result = await complete_tool_argument(tool_name, arg_name, arg_value, nixos_context, home_manager_context)

        # Verify search argument completion was called with correct arguments
        mock_search.assert_called_once_with(arg_name, arg_value, nixos_context)
        assert result == {"items": [{"label": "test", "value": "test"}]}


@pytest.mark.skip(reason="Skipped until MCP SDK implements completion/complete support")
@pytest.mark.asyncio
async def test_complete_tool_argument_home_manager_search():
    """Test tool argument completion for home_manager_search tool."""
    # Mock the contexts and dependencies
    nixos_context = MagicMock()
    home_manager_context = MagicMock()

    # Test home_manager_search tool arguments
    tool_name = "home_manager_search"
    arg_name = "query"
    arg_value = "test"

    # Mock the actual implementation function that gets called
    with patch("nixmcp.completions.complete_home_manager_search_arguments", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = {"items": [{"label": "test", "value": "test"}]}

        result = await complete_tool_argument(tool_name, arg_name, arg_value, nixos_context, home_manager_context)

        # Verify search argument completion was called with correct arguments
        mock_search.assert_called_once_with(arg_name, arg_value, home_manager_context)
        assert result == {"items": [{"label": "test", "value": "test"}]}


@pytest.mark.skip(reason="Skipped until MCP SDK implements completion/complete support")
@pytest.mark.asyncio
async def test_complete_tool_argument_unknown_tool():
    """Test tool argument completion for unknown tools."""
    # Mock the contexts and dependencies
    nixos_context = MagicMock()
    home_manager_context = MagicMock()

    # Test unknown tool
    tool_name = "unknown_tool"
    arg_name = "query"
    arg_value = "test"

    result = await complete_tool_argument(tool_name, arg_name, arg_value, nixos_context, home_manager_context)

    # Verify empty results are returned
    assert result == {"items": []}
