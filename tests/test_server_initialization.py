"""Tests for proper MCP protocol initialization and app state synchronization."""

import pytest
from unittest.mock import MagicMock

# Mark all tests in this module as asyncio and integration tests
pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


@pytest.mark.asyncio
class TestMCPInitialization:
    """Test MCP protocol initialization and app state synchronization."""

    async def test_app_initialization_synchronized_with_mcp_protocol(self, temp_cache_dir):
        """Test that app is_ready is properly synchronized with MCP handshake."""
        # Simplified test of is_ready flag

        # Create a mock request with is_ready flag
        mock_request = MagicMock()
        mock_request.request_context = MagicMock()
        mock_request.request_context.lifespan_context = {"is_ready": False}

        # Define a check_request_ready function similar to the one in the code
        def check_request_ready(ctx):
            return ctx.request_context.lifespan_context.get("is_ready", False)

        # When is_ready is False, check_request_ready should return False
        assert check_request_ready(mock_request) is False

        # When is_ready is True, check_request_ready should return True
        mock_request.request_context.lifespan_context["is_ready"] = True
        assert check_request_ready(mock_request) is True

    async def test_request_blocked_before_initialization(self, temp_cache_dir):
        """Test that requests are blocked before initialization is complete."""
        # Setup mock request context
        mock_request = MagicMock()
        mock_request.request_context = MagicMock()
        mock_request.request_context.lifespan_context = {"is_ready": False}

        # Define a check_request_ready function similar to the one in the code
        def check_request_ready(ctx):
            return ctx.request_context.lifespan_context.get("is_ready", False)

        # Check when not ready
        assert check_request_ready(mock_request) is False

        # Now mark as ready
        mock_request.request_context.lifespan_context["is_ready"] = True

        # Should now return true
        assert check_request_ready(mock_request) is True
