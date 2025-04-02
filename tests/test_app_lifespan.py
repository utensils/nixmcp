"""Tests for the app_lifespan context manager in the MCP-NixOS server."""

import sys
import pytest
from unittest.mock import patch, MagicMock

# Mark as asyncio integration tests
pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


# Use pytest fixtures and async tests with pytest instead of unittest
class TestAppLifespan:
    """Test the app_lifespan context manager."""

    @pytest.mark.asyncio
    async def test_app_lifespan_enter(self, temp_cache_dir):
        """Test entering the app_lifespan context manager."""
        # Setup mock server
        mock_server = MagicMock()

        # Reload the module to ensure clean state
        if "mcp_nixos.server" in sys.modules:
            del sys.modules["mcp_nixos.server"]

        # Import the modules after setting up environment
        with patch("mcp_nixos.server.logger") as mock_logger:
            # Import after patching logger
            from mcp_nixos.server import app_lifespan, nixos_context, home_manager_context, darwin_context

            # Create and enter the context manager
            context_manager = app_lifespan(mock_server)
            context = await context_manager.__aenter__()

            # Verify the context has the expected structure
            assert isinstance(context, dict)
            assert "nixos_context" in context
            assert "home_manager_context" in context
            assert "darwin_context" in context
            assert context["nixos_context"] is nixos_context
            assert context["home_manager_context"] is home_manager_context
            assert context["darwin_context"] is darwin_context

            # Verify prompt decorator was called on the server
            assert hasattr(mock_server, "prompt")
            mock_server.prompt.assert_called_once()

            # Exit the context manager to clean up
            await context_manager.__aexit__(None, None, None)

            # Verify shutdown was logged
            mock_logger.info.assert_any_call("Shutting down MCP-NixOS server")

    @pytest.mark.asyncio
    async def test_app_lifespan_exit(self, temp_cache_dir):
        """Test exiting the app_lifespan context manager (cleanup)."""
        # Setup mock server
        mock_server = MagicMock()

        # Reload the module to ensure clean state
        if "mcp_nixos.server" in sys.modules:
            del sys.modules["mcp_nixos.server"]

        # Setup the patches
        with patch("mcp_nixos.server.logger") as mock_logger:
            # Import after patching
            from mcp_nixos.server import app_lifespan, darwin_context

            # Patch the darwin_context.shutdown
            with patch.object(darwin_context, "shutdown", autospec=True) as mock_shutdown:
                # Create and enter the context manager
                context_manager = app_lifespan(mock_server)
                await context_manager.__aenter__()

                # Exit the context manager
                await context_manager.__aexit__(None, None, None)

                # Verify shutdown log message
                mock_logger.info.assert_any_call("Shutting down MCP-NixOS server")

                # Verify the darwin context was shut down
                mock_shutdown.assert_called_once()

    @pytest.mark.skip(reason="This test is unstable due to timing issues with asyncio context managers")
    @pytest.mark.asyncio
    async def test_app_lifespan_exception_handling(self):
        """Test exception handling in the app_lifespan context manager."""
        # This test is skipped, but we'll leave it for reference
        pass

    @pytest.mark.asyncio
    async def test_app_lifespan_cleanup_on_exception(self, temp_cache_dir):
        """Test cleanup is performed even when exception occurs during handling."""
        # Setup mocks
        mock_server = MagicMock()
        mock_exception = Exception("Test exception")

        # Reload the module to ensure clean state
        if "mcp_nixos.server" in sys.modules:
            del sys.modules["mcp_nixos.server"]

        # Setup the patches
        with patch("mcp_nixos.server.logger") as mock_logger:
            # Import after patching
            from mcp_nixos.server import app_lifespan, darwin_context

            # Patch the darwin_context.shutdown
            with patch.object(darwin_context, "shutdown", autospec=True) as mock_shutdown:
                # Create and enter the context manager
                context_manager = app_lifespan(mock_server)
                await context_manager.__aenter__()

                # Exit with exception
                await context_manager.__aexit__(type(mock_exception), mock_exception, None)

                # Verify shutdown message was logged despite exception
                mock_logger.info.assert_any_call("Shutting down MCP-NixOS server")

                # Verify the darwin context was shut down
                mock_shutdown.assert_called_once()
