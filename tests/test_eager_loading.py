"""Test for the eager loading of Home Manager data."""

import unittest
import logging
import asyncio
from unittest.mock import patch, MagicMock
from mcp.server.fastmcp import FastMCP

# Import the server module
from nixmcp.server import app_lifespan
from nixmcp.contexts.home_manager_context import HomeManagerContext as HMContext

# Disable logging during tests
logging.disable(logging.CRITICAL)


class TestEagerLoading(unittest.TestCase):
    """Test the eager loading functionality in the server."""

    @patch("nixmcp.server.home_manager_context")
    def test_app_lifespan_calls_ensure_loaded(self, mock_hm_context):
        """Test that app_lifespan calls ensure_loaded on the HomeManagerContext."""
        # Create a mock server
        mock_server = MagicMock()

        # Configure the mock home manager context
        mock_hm_context.ensure_loaded = MagicMock()

        # Create an async function to run the test
        async def run_test():
            # Call the app_lifespan context manager
            async with app_lifespan(mock_server):
                # The ensure_loaded call should happen during context entry
                pass

        # Run the async function
        asyncio.run(run_test())

        # Verify ensure_loaded was called
        mock_hm_context.ensure_loaded.assert_called_once()

    @patch("nixmcp.contexts.home_manager_context.HomeManagerClient")
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

        # Call ensure_loaded
        context.ensure_loaded()

        # Verify the client's ensure_loaded was called
        mock_client.ensure_loaded.assert_called_once()

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
        # Mock to track if ensure_loaded was called
        ensure_loaded_called = [False]

        # Create a mock async function for ensure_loaded
        original_ensure_loaded = HMContext.ensure_loaded

        def mock_ensure_loaded(self):
            ensure_loaded_called[0] = True
            # Call original to maintain behavior but avoid network calls
            if hasattr(self.hm_client, "is_loaded"):
                self.hm_client.is_loaded = True

        # Set up the mock
        HMContext.ensure_loaded = mock_ensure_loaded

        try:
            # Create a FastMCP server instance
            server = FastMCP("test", version="0.1.0", description="Test server")

            # Run the app_lifespan directly (blocking, not async for simplicity)
            async def run_lifespan():
                async with app_lifespan(server):
                    # Just yield to let the lifespan complete
                    await asyncio.sleep(0.1)

            # Run the test
            asyncio.run(run_lifespan())

            # Verify ensure_loaded was called
            self.assertTrue(ensure_loaded_called[0], "ensure_loaded was not called during app_lifespan")

        finally:
            # Restore original method
            HMContext.ensure_loaded = original_ensure_loaded


if __name__ == "__main__":
    unittest.main()
