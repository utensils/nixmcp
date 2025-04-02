"""Test for the eager loading of Home Manager data."""

import logging
import asyncio
import sys
import pytest
from unittest.mock import patch, MagicMock
from mcp.server.fastmcp import FastMCP

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Import required modules
from mcp_nixos.contexts.home_manager_context import HomeManagerContext as HMContext

# Disable logging during tests
logging.disable(logging.CRITICAL)


# Using pytest fixtures so we don't use unittest.TestCase here
class TestEagerLoading:

    @pytest.mark.asyncio
    async def test_app_lifespan_calls_load_in_background(self, temp_cache_dir):
        """Test that app_lifespan calls load_in_background on the HomeManagerContext's client."""
        # Create a mock server
        mock_server = MagicMock()

        # Reload the server module to ensure clean state
        if "mcp_nixos.server" in sys.modules:
            del sys.modules["mcp_nixos.server"]

        # Import and patch in the correct order
        with patch("mcp_nixos.server.home_manager_context") as mock_hm_context:
            # Setup the mock client
            mock_client = MagicMock()
            mock_hm_context.hm_client = mock_client

            # Import after patching
            from mcp_nixos.server import app_lifespan

            # Call the app_lifespan context manager
            async with app_lifespan(mock_server):
                # The load_in_background call should happen during context entry
                pass

            # Verify load_in_background was called on the client
            mock_client.load_in_background.assert_called_once()

    def test_home_manager_context_ensures_loaded(self):
        """Test that the HomeManagerContext.ensure_loaded calls the client's ensure_loaded."""
        # Create a mock client
        with patch("mcp_nixos.contexts.home_manager_context.HomeManagerClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.is_loaded = False
            mock_client.loading_error = None
            mock_client.loading_in_progress = False
            mock_client.loading_thread = None
            mock_client.loading_lock = MagicMock()

            # Configure the mock class to return our mock client
            mock_client_class.return_value = mock_client

            # Create a context that will use our mock client
            context = HMContext()

            # Call ensure_loaded normally
            context.ensure_loaded()

            # Verify the client's ensure_loaded was called with correct params
            mock_client.ensure_loaded.assert_called_with(force_refresh=False)

            # Reset the mock for the next test
            mock_client.ensure_loaded.reset_mock()

            # Call ensure_loaded with force_refresh=True
            context.ensure_loaded(force_refresh=True)

            # Verify the client's ensure_loaded was called with force_refresh=True
            mock_client.ensure_loaded.assert_called_with(force_refresh=True)

    def test_cache_invalidation(self):
        """Test the cache invalidation functionality."""
        # Create a mock client
        with patch("mcp_nixos.contexts.home_manager_context.HomeManagerClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.is_loaded = True

            # Configure the mock class to return our mock client
            mock_client_class.return_value = mock_client

            # Create a context that will use our mock client
            context = HMContext()

            # Call invalidate_cache
            context.invalidate_cache()

            # Verify the client's invalidate_cache was called
            mock_client.invalidate_cache.assert_called_once()

    @pytest.mark.integration
    def test_integration_from_context_to_client(self):
        """Test the full integration from context to client ensure_loaded."""
        # Create a fully-populated mock client
        mock_client = MagicMock()
        mock_client.is_loaded = True
        mock_client.loading_error = None
        mock_client.loading_in_progress = False
        mock_client.loading_thread = None
        mock_client.loading_lock = MagicMock()
        mock_client.get_stats.return_value = {
            "total_options": 100,
            "by_source": {"options": 50, "nixos-options": 50},
            "found": True,
        }
        mock_client.cache = MagicMock()
        mock_client.cache.get_stats.return_value = {
            "hits": 10,
            "misses": 5,
            "cache_dir": "/tmp/cache",
            "file_count": 10,
        }

        # Create a context with our mock
        context = HMContext()
        context.hm_client = mock_client

        # Call ensure_loaded
        context.ensure_loaded()

        # Verify the client's ensure_loaded was called
        mock_client.ensure_loaded.assert_called_once()

        # Then get status to verify everything is connected
        status = context.get_status()

        # Verify the status indicates success
        assert status["status"] == "ok"
        assert status["options_count"] == 100
        assert "cache_stats" in status

    @pytest.mark.asyncio
    async def test_run_server_lifespan(self, temp_cache_dir):
        """Run an integrated server lifespan with eager loading test."""
        # Create a mock server
        server = FastMCP("test", version="0.1.0", description="Test server")

        # Reload the server module to ensure clean state
        if "mcp_nixos.server" in sys.modules:
            del sys.modules["mcp_nixos.server"]

        # Create patches for all relevant parts
        with patch("mcp_nixos.server.home_manager_context") as mock_hm_context:
            with patch("mcp_nixos.server.darwin_context") as mock_darwin_context:
                # Setup the mock client
                mock_client = MagicMock()
                mock_hm_context.hm_client = mock_client

                # Setup darwin context
                mock_darwin_context.startup = MagicMock()
                mock_darwin_context.shutdown = MagicMock()
                mock_darwin_context.status = "loaded"

                # Import after patching
                from mcp_nixos.server import app_lifespan

                # Run the app_lifespan directly
                async with app_lifespan(server):
                    # Just yield to let the lifespan complete
                    await asyncio.sleep(0.1)

                # Verify load_in_background was called
                mock_client.load_in_background.assert_called_once()

                # Verify darwin context was managed properly
                mock_darwin_context.startup.assert_called_once()
                mock_darwin_context.shutdown.assert_called_once()


# No unittest.main() needed with pytest
