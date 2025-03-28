"""Test integration of nix-darwin functionality."""

import os
import pathlib
import pytest
from unittest.mock import MagicMock, AsyncMock

from nixmcp.clients.darwin.darwin_client import DarwinClient
from nixmcp.contexts.darwin.darwin_context import DarwinContext
from nixmcp.utils.cache_helpers import get_default_cache_dir
from nixmcp.tools.darwin.darwin_tools import (
    darwin_search,
    darwin_info,
    darwin_stats,
    darwin_list_options,
    darwin_options_by_prefix,
)

# Darwin resources are only used through the context in tests


@pytest.fixture
def mock_darwin_client():
    """Create a mock Darwin client for testing."""
    client = MagicMock(spec=DarwinClient)

    # Mock the async methods
    client.load_options = AsyncMock(return_value={})
    client.search_options = AsyncMock(
        return_value=[
            {"name": "system.defaults.dock.autohide", "description": "Whether to automatically hide and show the dock."}
        ]
    )
    client.get_option = AsyncMock(
        return_value={
            "name": "system.defaults.dock.autohide",
            "description": "Whether to automatically hide and show the dock.",
            "type": "bool",
            "default": "false",
            "example": "true",
            "declared_by": "system/defaults.nix",
            "sub_options": [],
        }
    )
    client.get_options_by_prefix = AsyncMock(
        return_value=[
            {
                "name": "system.defaults.dock.autohide",
                "description": "Whether to automatically hide and show the dock.",
            },
            {"name": "system.defaults.dock.orientation", "description": "Position of the dock on screen."},
        ]
    )
    client.get_categories = AsyncMock(
        return_value=[
            {"name": "system", "option_count": 10, "path": "system"},
            {"name": "services", "option_count": 15, "path": "services"},
        ]
    )
    client.get_statistics = AsyncMock(
        return_value={
            "total_options": 100,
            "total_categories": 10,
            "last_updated": "2025-03-26T12:00:00",
            "loading_status": "loaded",
            "categories": [
                {"name": "system", "option_count": 10, "path": "system"},
                {"name": "services", "option_count": 15, "path": "services"},
            ],
        }
    )

    return client


@pytest.fixture
def mock_darwin_context(mock_darwin_client):
    """Create a mock Darwin context for testing."""
    context = MagicMock(spec=DarwinContext)
    context.status = "loaded"
    context.search_options = AsyncMock(
        return_value=[
            {"name": "system.defaults.dock.autohide", "description": "Whether to automatically hide and show the dock."}
        ]
    )
    context.get_option = AsyncMock(
        return_value={
            "name": "system.defaults.dock.autohide",
            "description": "Whether to automatically hide and show the dock.",
            "type": "bool",
            "default": "false",
            "example": "true",
            "declared_by": "system/defaults.nix",
            "sub_options": [],
        }
    )
    context.get_options_by_prefix = AsyncMock(
        return_value=[
            {
                "name": "system.defaults.dock.autohide",
                "description": "Whether to automatically hide and show the dock.",
            },
            {"name": "system.defaults.dock.orientation", "description": "Position of the dock on screen."},
        ]
    )
    context.get_categories = AsyncMock(
        return_value=[
            {"name": "system", "option_count": 10, "path": "system"},
            {"name": "services", "option_count": 15, "path": "services"},
        ]
    )
    context.get_statistics = AsyncMock(
        return_value={
            "total_options": 100,
            "total_categories": 10,
            "last_updated": "2025-03-26T12:00:00",
            "loading_status": "loaded",
            "categories": [
                {"name": "system", "option_count": 10, "path": "system"},
                {"name": "services", "option_count": 15, "path": "services"},
            ],
        }
    )
    return context


@pytest.mark.asyncio
async def test_darwin_search(mock_darwin_context):
    """Test darwin_search tool."""
    result = await darwin_search("dock", limit=10, context=mock_darwin_context)
    assert "dock" in result
    assert "autohide" in result
    mock_darwin_context.search_options.assert_called_once_with("dock", limit=10)


@pytest.mark.asyncio
async def test_darwin_info(mock_darwin_context):
    """Test darwin_info tool."""
    result = await darwin_info("system.defaults.dock.autohide", context=mock_darwin_context)
    assert "system.defaults.dock.autohide" in result
    assert "Whether to automatically hide" in result
    assert "Type:" in result
    assert "Default:" in result
    mock_darwin_context.get_option.assert_called_once_with("system.defaults.dock.autohide")


@pytest.mark.asyncio
async def test_darwin_stats(mock_darwin_context):
    """Test darwin_stats tool."""
    result = await darwin_stats(context=mock_darwin_context)
    assert "nix-darwin Options Statistics" in result
    assert "Total options:** 100" in result
    assert "system" in result
    assert "services" in result
    mock_darwin_context.get_statistics.assert_called_once()


@pytest.mark.asyncio
async def test_darwin_list_options(mock_darwin_context):
    """Test darwin_list_options tool."""
    result = await darwin_list_options(context=mock_darwin_context)
    assert "nix-darwin Option Categories" in result
    assert "system" in result
    assert "services" in result
    mock_darwin_context.get_categories.assert_called_once()


@pytest.mark.asyncio
async def test_darwin_options_by_prefix(mock_darwin_context):
    """Test darwin_options_by_prefix tool."""
    result = await darwin_options_by_prefix("system.defaults.dock", context=mock_darwin_context)
    assert "nix-darwin options with prefix 'system.defaults.dock'" in result
    assert "autohide" in result
    assert "orientation" in result
    mock_darwin_context.get_options_by_prefix.assert_called_once_with("system.defaults.dock")


@pytest.mark.asyncio
async def test_darwin_search_error_handling(mock_darwin_context):
    """Test error handling in darwin_search tool."""
    mock_darwin_context.search_options = AsyncMock(side_effect=ValueError("Test error"))
    result = await darwin_search("dock", context=mock_darwin_context)
    assert "Error" in result
    assert "Test error" in result


@pytest.mark.asyncio
async def test_darwin_info_not_found(mock_darwin_context):
    """Test handling of not found options in darwin_info tool."""
    mock_darwin_context.get_option = AsyncMock(return_value=None)
    result = await darwin_info("nonexistent.option", context=mock_darwin_context)
    assert "not found" in result


def test_darwin_integration_cache_directory():
    """
    Test that a real DarwinContext and DarwinClient use the proper cache directory.

    This is an integration test that verifies the fix for the issue where the client
    was trying to create a 'darwin' directory in the current working directory
    instead of using the proper OS-specific cache path.

    This test also verifies that the client doesn't create cache files with empty data.
    """
    # We're just creating the objects, not actually loading data
    context = DarwinContext()

    # Verify the client exists and has an html_cache
    assert context.client is not None
    assert hasattr(context.client, "html_cache")

    # Verify cache directory path
    cache_dir = context.client.html_cache.cache_dir

    # Ensure cache_dir is a proper path object
    assert isinstance(cache_dir, pathlib.Path)

    # Check it's not using the incorrect 'darwin' relative path
    assert cache_dir != pathlib.Path("darwin")

    # Check it's using a subdirectory of the default cache location
    default_cache_dir = pathlib.Path(get_default_cache_dir())
    assert str(cache_dir).startswith(str(default_cache_dir))

    # The directory should exist and be writeable
    assert cache_dir.exists()
    assert os.access(str(cache_dir), os.W_OK)

    # Check that there's no 'darwin' directory in current working directory
    darwin_dir = pathlib.Path.cwd() / "darwin"
    if darwin_dir.exists():
        # If it does exist (maybe from previous tests), it shouldn't be
        # the same as our cache directory
        assert darwin_dir != cache_dir

    # Get the cache key
    cache_key = context.client.cache_key

    # Check that no empty data files were created
    json_path = context.client.html_client.cache._get_data_cache_path(cache_key)
    # pickle_path not used but kept for reference
    # pickle_path = context.client.html_client.cache._get_binary_data_cache_path(cache_key)

    # If these exist, they should contain valid data (not empty)
    if json_path.exists():
        with open(json_path, "r") as f:
            import json as json_module

            data = json_module.load(f)
            # Verify we don't have zero options cached
            if "total_options" in data:
                assert data["total_options"] > 0, "Cache has zero options - invalid data was cached"
            if "options" in data:
                assert len(data["options"]) > 0, "Cache has empty options dict - invalid data was cached"
