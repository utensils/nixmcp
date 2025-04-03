"""Tests for proper coroutine handling in nix-darwin MCP tools.

This test file specifically focuses on ensuring that async functions
are properly awaited in the MCP tool handlers.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
import inspect

# Mark all tests in this module as asyncio and integration tests
pytestmark = [pytest.mark.integration]

from mcp_nixos.tools.darwin.darwin_tools import (
    darwin_search,
    darwin_info,
    darwin_stats,
    darwin_list_options,
    darwin_options_by_prefix,
    register_darwin_tools,
)


@pytest.fixture
def mock_darwin_context():
    """Create a mock Darwin context for testing."""
    context = MagicMock()
    context.search_options = AsyncMock(return_value=[{"name": "test.option", "description": "Test option"}])
    context.get_option = AsyncMock(
        return_value={
            "name": "test.option",
            "description": "Test option",
            "type": "string",
        }
    )
    context.get_options_by_prefix = AsyncMock(return_value=[{"name": "test.option", "description": "Test option"}])
    context.get_categories = AsyncMock(return_value=[{"name": "test", "option_count": 1, "path": "test"}])
    context.get_statistics = AsyncMock(
        return_value={
            "total_options": 1,
            "total_categories": 1,
            "last_updated": "2025-03-26T12:00:00",
            "loading_status": "loaded",
            "categories": [{"name": "test", "option_count": 1, "path": "test"}],
        }
    )
    return context


@pytest.fixture
def mock_mcp():
    """Create a mock MCP server."""
    mcp = MagicMock()
    # Create a properly mocked tool decorator that can track calls

    # Make the tool decorator return the function unchanged
    def tool_decorator(name):
        tool_decorator.call_count += 1
        tool_decorator.call_args_list.append((name,))
        return lambda func: func

    tool_decorator.call_count = 0
    tool_decorator.call_args_list = []
    mcp.tool = tool_decorator
    return mcp


class TestDarwinToolsCoroutine:
    """Test class for darwin tools coroutine handling."""

    def test_tool_functions_are_async(self):
        """Test that all darwin tool functions are declared as async."""
        assert inspect.iscoroutinefunction(darwin_search)
        assert inspect.iscoroutinefunction(darwin_info)
        assert inspect.iscoroutinefunction(darwin_stats)
        assert inspect.iscoroutinefunction(darwin_list_options)
        assert inspect.iscoroutinefunction(darwin_options_by_prefix)

    def test_register_darwin_tools_creates_async_handlers(self, mock_darwin_context, mock_mcp):
        """Test that register_darwin_tools creates async handler functions."""
        # Call the register function with our mocks
        register_darwin_tools(mock_darwin_context, mock_mcp)

        # The tool decorator should have been called 5 times (once for each tool)
        assert mock_mcp.tool.call_count == 5

        # Test that all the tool names were registered
        expected_tools = {
            "darwin_search",
            "darwin_info",
            "darwin_stats",
            "darwin_list_options",
            "darwin_options_by_prefix",
        }

        registered_tools = {call[0] for call in mock_mcp.tool.call_args_list}
        assert registered_tools == expected_tools

    @pytest.mark.asyncio
    async def test_darwin_search_returns_string(self, mock_darwin_context):
        """Test that darwin_search returns a string, not a coroutine."""
        # Call the function
        result = await darwin_search("test", context=mock_darwin_context)

        # Verify the result is a string, not a coroutine
        assert isinstance(result, str)
        assert not inspect.iscoroutine(result)

        # Verify the context method was called
        mock_darwin_context.search_options.assert_called_once()

    @pytest.mark.asyncio
    async def test_darwin_info_returns_string(self, mock_darwin_context):
        """Test that darwin_info returns a string, not a coroutine."""
        # Call the function
        result = await darwin_info("test.option", context=mock_darwin_context)

        # Verify the result is a string, not a coroutine
        assert isinstance(result, str)
        assert not inspect.iscoroutine(result)

        # Verify the context method was called
        mock_darwin_context.get_option.assert_called_once()

    @pytest.mark.asyncio
    async def test_darwin_stats_returns_string(self, mock_darwin_context):
        """Test that darwin_stats returns a string, not a coroutine."""
        # Call the function
        result = await darwin_stats(context=mock_darwin_context)

        # Verify the result is a string, not a coroutine
        assert isinstance(result, str)
        assert not inspect.iscoroutine(result)

        # Verify the context method was called
        mock_darwin_context.get_statistics.assert_called_once()

    @pytest.mark.asyncio
    async def test_darwin_list_options_returns_string(self, mock_darwin_context):
        """Test that darwin_list_options returns a string, not a coroutine."""
        # Call the function
        result = await darwin_list_options(context=mock_darwin_context)

        # Verify the result is a string, not a coroutine
        assert isinstance(result, str)
        assert not inspect.iscoroutine(result)

        # Verify the context method was called
        mock_darwin_context.get_categories.assert_called_once()

    @pytest.mark.asyncio
    async def test_darwin_options_by_prefix_returns_string(self, mock_darwin_context):
        """Test that darwin_options_by_prefix returns a string, not a coroutine."""
        # Call the function
        result = await darwin_options_by_prefix("test", context=mock_darwin_context)

        # Verify the result is a string, not a coroutine
        assert isinstance(result, str)
        assert not inspect.iscoroutine(result)

        # Verify the context method was called
        mock_darwin_context.get_options_by_prefix.assert_called_once()


class TestToolHandlerAwait:
    """Test that tool handlers properly await coroutines."""

    @pytest.mark.asyncio
    async def test_darwin_search_handler_awaits_coroutine(self, mock_darwin_context):
        """Test that darwin_search is properly awaited in the handler function."""

        # Create a handler that mimics the one in register_darwin_tools
        async def darwin_search_handler(query: str, limit: int = 20):
            return await darwin_search(query, limit, mock_darwin_context)

        # Call the handler function directly
        result = await darwin_search_handler("test", 10)

        # Verify the result is a string, not a coroutine
        assert isinstance(result, str)
        assert not inspect.iscoroutine(result)

        # Verify the context method was called with the right arguments
        mock_darwin_context.search_options.assert_called_once_with("test", limit=10)

    @pytest.mark.asyncio
    async def test_darwin_info_handler_awaits_coroutine(self, mock_darwin_context):
        """Test that darwin_info is properly awaited in the handler function."""

        # Create a handler that mimics the one in register_darwin_tools
        async def darwin_info_handler(name: str):
            return await darwin_info(name, mock_darwin_context)

        # Call the handler function directly
        result = await darwin_info_handler("test.option")

        # Verify the result is a string, not a coroutine
        assert isinstance(result, str)
        assert not inspect.iscoroutine(result)

        # Verify the context method was called with the right arguments
        mock_darwin_context.get_option.assert_called_once_with("test.option")

    @pytest.mark.asyncio
    async def test_darwin_stats_handler_awaits_coroutine(self, mock_darwin_context):
        """Test that darwin_stats is properly awaited in the handler function."""

        # Create a handler that mimics the one in register_darwin_tools
        async def darwin_stats_handler():
            return await darwin_stats(mock_darwin_context)

        # Call the handler function directly
        result = await darwin_stats_handler()

        # Verify the result is a string, not a coroutine
        assert isinstance(result, str)
        assert not inspect.iscoroutine(result)

        # Verify the context method was called
        mock_darwin_context.get_statistics.assert_called_once()

    @pytest.mark.asyncio
    async def test_darwin_list_options_handler_awaits_coroutine(self, mock_darwin_context):
        """Test that darwin_list_options is properly awaited in the handler function."""

        # Create a handler that mimics the one in register_darwin_tools
        async def darwin_list_options_handler():
            return await darwin_list_options(mock_darwin_context)

        # Call the handler function directly
        result = await darwin_list_options_handler()

        # Verify the result is a string, not a coroutine
        assert isinstance(result, str)
        assert not inspect.iscoroutine(result)

        # Verify the context method was called
        mock_darwin_context.get_categories.assert_called_once()

    @pytest.mark.asyncio
    async def test_darwin_options_by_prefix_handler_awaits_coroutine(self, mock_darwin_context):
        """Test that darwin_options_by_prefix is properly awaited in the handler function."""

        # Create a handler that mimics the one in register_darwin_tools
        async def darwin_options_by_prefix_handler(option_prefix: str):
            return await darwin_options_by_prefix(option_prefix, mock_darwin_context)

        # Call the handler function directly
        result = await darwin_options_by_prefix_handler("test")

        # Verify the result is a string, not a coroutine
        assert isinstance(result, str)
        assert not inspect.iscoroutine(result)

        # Verify the context method was called with the right arguments
        mock_darwin_context.get_options_by_prefix.assert_called_once_with("test")
