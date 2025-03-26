"""
Tests for Home Manager-specific MCP completion implementations.

This module tests the Home Manager-specific completion implementations for options
and tool arguments.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nixmcp.completions.home_manager import (
    complete_home_manager_option_name,
    complete_home_manager_search_arguments,
    complete_home_manager_info_arguments,
    complete_home_manager_prefix_arguments,
)


@pytest.mark.asyncio
async def test_complete_home_manager_option_name_empty():
    """Test Home Manager option name completion with empty input."""
    # Mock Home Manager client
    hm_client = MagicMock()

    # Test with empty option name
    result = await complete_home_manager_option_name("", hm_client)

    # Verify default suggestions are returned
    assert isinstance(result, dict)
    assert "items" in result
    assert len(result["items"]) > 0
    assert all(isinstance(item, dict) for item in result["items"])
    assert all("label" in item and "value" in item for item in result["items"])


@pytest.mark.asyncio
async def test_complete_home_manager_option_name_exact_prefix():
    """Test Home Manager option name completion with exact prefix match."""
    # Mock Home Manager client with prefix index
    hm_client = MagicMock()
    hm_client.prefix_index = {"programs.git": {"programs.git.enable", "programs.git.userName"}}
    hm_client.options_data = {
        "programs.git.enable": {"description": "Whether to enable Git", "type": "boolean"},
        "programs.git.userName": {"description": "User name for Git", "type": "string"},
    }

    # Test with exact prefix match
    result = await complete_home_manager_option_name("programs.git", hm_client)

    # Verify options with matching prefix are returned
    assert isinstance(result, dict)
    assert "items" in result
    assert len(result["items"]) == 2
    option_labels = {item["label"] for item in result["items"]}
    assert "programs.git.enable" in option_labels
    assert "programs.git.userName" in option_labels


@pytest.mark.asyncio
async def test_complete_home_manager_option_name_hierarchical():
    """Test Home Manager option name completion with hierarchical path."""
    # Mock Home Manager client with hierarchical index
    hm_client = MagicMock()
    hm_client.hierarchical_index = {
        "programs.git": {"enable": {"programs.git.enable"}, "userName": {"programs.git.userName"}}
    }
    hm_client.options_data = {
        "programs.git.enable": {"description": "Whether to enable Git", "type": "boolean"},
        "programs.git.userName": {"description": "User name for Git", "type": "string"},
    }

    # Test with hierarchical path
    result = await complete_home_manager_option_name("programs.git.e", hm_client)

    # Verify hierarchical-based matching works
    assert isinstance(result, dict)
    assert "items" in result
    assert len(result["items"]) == 1
    assert result["items"][0]["label"] == "programs.git.enable"
    assert result["items"][0]["value"] == "programs.git.enable"


@pytest.mark.asyncio
async def test_complete_home_manager_search_arguments_query_empty():
    """Test Home Manager search arguments completion for empty query parameter."""
    # Mock Home Manager context
    home_manager_context = MagicMock()

    # Test with empty query
    result = await complete_home_manager_search_arguments("query", "", home_manager_context)

    # Verify default suggestions are returned
    assert isinstance(result, dict)
    assert "items" in result
    assert len(result["items"]) > 0
    assert all(isinstance(item, dict) for item in result["items"])
    assert all("label" in item and "value" in item for item in result["items"])


@pytest.mark.asyncio
async def test_complete_home_manager_search_arguments_query():
    """Test Home Manager search arguments completion for query parameter."""
    # Mock Home Manager context and client
    home_manager_context = MagicMock()
    hm_client = MagicMock()
    home_manager_context.get_home_manager_client.return_value = hm_client

    # Mock option name completion
    with patch(
        "nixmcp.completions.home_manager.complete_home_manager_option_name", new_callable=AsyncMock
    ) as mock_option:
        mock_option.return_value = {"items": [{"label": "programs.git", "value": "programs.git"}]}

        # Test with query argument
        result = await complete_home_manager_search_arguments("query", "programs.git", home_manager_context)

        # Verify option completion was called with is_search=True
        mock_option.assert_called_once_with("programs.git", hm_client, is_search=True)
        assert result == {"items": [{"label": "programs.git", "value": "programs.git"}]}


@pytest.mark.asyncio
async def test_complete_home_manager_search_arguments_limit():
    """Test Home Manager search arguments completion for limit parameter."""
    # Mock Home Manager context
    home_manager_context = MagicMock()

    # Test with limit argument
    result = await complete_home_manager_search_arguments("limit", "1", home_manager_context)

    # Verify limit suggestions are returned
    assert isinstance(result, dict)
    assert "items" in result
    assert len(result["items"]) > 0
    assert all(isinstance(item, dict) for item in result["items"])
    assert all("label" in item and "value" in item for item in result["items"])

    # Verify all suggestions are numeric
    assert all(item["label"].isdigit() for item in result["items"])


@pytest.mark.asyncio
async def test_complete_home_manager_info_arguments_name():
    """Test Home Manager info arguments completion for name parameter."""
    # Mock Home Manager context and client
    home_manager_context = MagicMock()
    hm_client = MagicMock()
    home_manager_context.get_home_manager_client.return_value = hm_client

    # Mock option name completion
    with patch(
        "nixmcp.completions.home_manager.complete_home_manager_option_name", new_callable=AsyncMock
    ) as mock_option:
        mock_option.return_value = {"items": [{"label": "programs.git.enable", "value": "programs.git.enable"}]}

        # Test with name argument
        result = await complete_home_manager_info_arguments("name", "programs.git", home_manager_context)

        # Verify option completion was called
        mock_option.assert_called_once_with("programs.git", hm_client)
        assert result == {"items": [{"label": "programs.git.enable", "value": "programs.git.enable"}]}


@pytest.mark.asyncio
async def test_complete_home_manager_prefix_arguments_empty():
    """Test Home Manager prefix arguments completion for empty option_prefix parameter."""
    # Mock Home Manager context
    home_manager_context = MagicMock()

    # Test with empty option_prefix
    result = await complete_home_manager_prefix_arguments("option_prefix", "", home_manager_context)

    # Verify default suggestions are returned
    assert isinstance(result, dict)
    assert "items" in result
    assert len(result["items"]) > 0
    assert all(isinstance(item, dict) for item in result["items"])
    assert all("label" in item and "value" in item for item in result["items"])


@pytest.mark.asyncio
async def test_complete_home_manager_prefix_arguments():
    """Test Home Manager prefix arguments completion for option_prefix parameter."""
    # Mock Home Manager context and client
    home_manager_context = MagicMock()
    hm_client = MagicMock()
    home_manager_context.get_home_manager_client.return_value = hm_client

    # Mock option name completion
    with patch(
        "nixmcp.completions.home_manager.complete_home_manager_option_name", new_callable=AsyncMock
    ) as mock_option:
        mock_option.return_value = {"items": [{"label": "programs.git", "value": "programs.git"}]}

        # Test with option_prefix argument
        result = await complete_home_manager_prefix_arguments("option_prefix", "programs", home_manager_context)

        # Verify option completion was called
        mock_option.assert_called_once_with("programs", hm_client)
        assert result == {"items": [{"label": "programs.git", "value": "programs.git"}]}
