"""Test for the eager loading of Home Manager data."""

import unittest
import logging
import asyncio
from unittest.mock import patch, MagicMock
from mcp.server.fastmcp import FastMCP

# Import the server module
from mcp_nixos.server import app_lifespan
from mcp_nixos.contexts.home_manager_context import HomeManagerContext as HMContext

# Disable logging during tests
logging.disable(logging.CRITICAL)


class TestEagerLoading(unittest.TestCase):
    """Test the eager loading functionality in the server."""

    @patch("mcp_nixos.server.home_manager_context")
    def test_app_lifespan_calls_load_in_background(self, mock_hm_context):
        """Test that app_lifespan calls load_in_background on the HomeManagerContext's client."""
        # Create a mock server
        mock_server = MagicMock()

        # Create a mock client with load_in_background that we can track
        mock_client = MagicMock()
        mock_hm_context.hm_client = mock_client

        # Add missing attributes needed by the lifespan
        mock_hm_context.loading_error = None
        mock_hm_context.is_loaded = True
        mock_hm_context.search_options = MagicMock()
        mock_hm_context.get_option = MagicMock()
        mock_hm_context.get_stats = MagicMock()

        # Create an async function to run the test
        async def run_test():
            # Call the app_lifespan context manager
            async with app_lifespan(mock_server):
                # The load_in_background call should happen during context entry
                pass

        # Run the async function
        asyncio.run(run_test())

        # Verify load_in_background was called on the client
        self.assertTrue(mock_client.load_in_background.called, "load_in_background was not called during app_lifespan")

    @patch("mcp_nixos.contexts.home_manager_context.HomeManagerClient")
    def test_home_manager_context_ensures_loaded(self, mock_client_class):
        """Test that the HomeManagerContext.ensure_loaded calls the client's ensure_loaded."""
        # Create a mock client
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

    @patch("mcp_nixos.contexts.home_manager_context.HomeManagerClient")
    def test_cache_invalidation(self, mock_client_class):
        """Test the cache invalidation functionality."""
        # Create a mock client
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
        self.assertEqual(status["status"], "ok")
        self.assertEqual(status["options_count"], 100)
        self.assertIn("cache_stats", status)

    def test_run_server_lifespan(self):
        """Run an integrated server lifespan with eager loading test."""
        # Create a mock and patch it in place
        with patch("mcp_nixos.server.home_manager_context") as mock_hm_context:
            # Create a mock client with load_in_background that we can track
            mock_client = MagicMock()
            mock_hm_context.hm_client = mock_client

            # Add missing attributes needed by the lifespan
            mock_hm_context.loading_error = None
            mock_hm_context.is_loaded = True
            mock_hm_context.search_options = MagicMock()
            mock_hm_context.get_option = MagicMock()
            mock_hm_context.get_stats = MagicMock()

            # Create a FastMCP server instance
            server = FastMCP("test", version="0.1.0", description="Test server")

            # Run the app_lifespan directly
            async def run_lifespan():
                async with app_lifespan(server):
                    # Just yield to let the lifespan complete
                    await asyncio.sleep(0.1)

            # Run the test
            asyncio.run(run_lifespan())

            # Verify load_in_background was called
            self.assertTrue(
                mock_client.load_in_background.called, "load_in_background was not called during app_lifespan"
            )


if __name__ == "__main__":
    unittest.main()
