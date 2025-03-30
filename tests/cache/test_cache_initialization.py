"""Tests for cache initialization and fallback behavior."""

import os
import sys
import tempfile
import pathlib
import pytest
from unittest.mock import patch, MagicMock

# Mark as unit tests (not integration)
pytestmark = [pytest.mark.unit, pytest.mark.not_integration]

from mcp_nixos.cache.html_cache import HTMLCache
from mcp_nixos.clients.html_client import HTMLClient
from mcp_nixos.utils.cache_helpers import init_cache_storage, get_default_cache_dir


class TestCacheInitialization:
    """Test cache initialization, directory creation, and fallback behaviors."""

    def test_html_cache_initialization_failure(self):
        """Test that HTMLCache gracefully handles initialization failures."""
        # Create a mock that will cause ensure_cache_dir to fail
        with patch("mcp_nixos.utils.cache_helpers.ensure_cache_dir") as mock_ensure_dir:
            mock_ensure_dir.side_effect = PermissionError("Permission denied creating cache directory")

            # Initialize HTMLCache - should fall back to temp directory
            cache = HTMLCache()

            # Verify cache was initialized with a fallback path
            assert cache.config["initialized"] is False
            assert "error" in cache.config
            assert "Permission denied" in cache.config["error"]

            # Ensure we still have a valid cache_dir
            assert cache.cache_dir is not None
            assert pathlib.Path(cache.cache_dir).exists()

            # Test that basic operations still work with fallback cache
            url = "https://example.com/test"
            cache.set(url, "<html>Test</html>")
            content, metadata = cache.get(url)
            assert content == "<html>Test</html>"

    def test_init_cache_storage_fallback(self):
        """Test that init_cache_storage provides a working fallback when directory creation fails."""
        # Force ensure_cache_dir to fail
        with patch("mcp_nixos.utils.cache_helpers.ensure_cache_dir") as mock_ensure_dir:
            mock_ensure_dir.side_effect = PermissionError("Permission denied")

            # Initialize cache storage - should fall back to temp directory
            config = init_cache_storage()

            # Verify we got a fallback configuration
            assert config["initialized"] is False
            assert "error" in config
            assert "Permission denied" in config["error"]
            assert "cache_dir" in config
            assert os.path.exists(config["cache_dir"])

    def test_html_client_cache_initialization_failure(self):
        """Test that HTMLClient handles cache initialization failure gracefully."""
        # Force cache initialization to fail
        with patch("mcp_nixos.cache.html_cache.init_cache_storage") as mock_init:
            # Return a valid fallback config
            mock_init.return_value = {
                "cache_dir": tempfile.gettempdir(),
                "ttl": 86400,
                "initialized": False,
                "error": "Permission denied",
            }

            # Initialize HTMLClient - should use fallback path
            client = HTMLClient()

            # Verify client has an initialized cache
            assert client.cache is not None
            assert client.cache.config["initialized"] is False
            assert client.cache.cache_dir is not None

            # Test to ensure client still works
            with patch("requests.get") as mock_get:
                mock_response = MagicMock()
                mock_response.text = "<html>Test</html>"
                mock_response.status_code = 200
                mock_response.raise_for_status = MagicMock()
                mock_get.return_value = mock_response

                # Fetch content - should work despite initialization failure
                content, metadata = client.fetch("https://example.com/test")
                assert content == "<html>Test</html>"
                assert metadata["success"] is True

    @pytest.mark.asyncio
    async def test_server_initialization_with_cache_failure(self):
        """Test that server initialization handles cache directory creation failure gracefully."""
        # To properly test this without circular imports:
        # 1. Patch the ensure_cache_dir function to fail when called during module initialization
        # 2. Monitor that HTMLClient and other components still initialize with fallback paths

        # Create a patch to make ensure_cache_dir fail
        with patch("mcp_nixos.utils.cache_helpers.ensure_cache_dir") as mock_ensure_dir:
            mock_ensure_dir.side_effect = PermissionError("Permission denied")

            # We need to import these here after the patch so it affects module initialization
            from mcp_nixos.contexts.darwin.darwin_context import DarwinContext

            # Create context with the patched cache helpers
            darwin_context = DarwinContext()

            # Verify that despite cache initialization failure, we still have a working context
            assert darwin_context is not None
            assert darwin_context.client is not None

            # Test that we can use the context - monkey patch the load_options to avoid real network calls
            with patch.object(darwin_context.client, "load_options", new_callable=MagicMock) as mock_load:
                mock_load.return_value = {}

                # Start the context - this would fail if cache initialization completely breaks the system
                await darwin_context.startup()

                # Verify the context status
                # For this test, we expect an error since we're patching functionality
                # We just want to verify the context doesn't crash on initialization
                assert darwin_context.status is not None

                # Shut down properly to clean up
                await darwin_context.shutdown()

    def test_cache_never_uses_system_directory(self, temp_cache_dir):
        """Test that tests never use the system-default cache directory."""
        # Get the default system cache directory
        system_cache_dir = get_default_cache_dir()

        # Initialize cache without explicit directory
        # The temp_cache_dir fixture should have set the environment variable
        config = init_cache_storage()

        # The resulting cache dir should NEVER be the system default
        assert config["cache_dir"] != system_cache_dir, "Cache is using system directory during tests"

        # It should match our test-specific directory pattern
        assert (
            "mcp_nixos_test_cache" in config["cache_dir"]
        ), f"Cache directory {config['cache_dir']} doesn't include the test pattern"

        # Explicitly verify we didn't touch the system directory
        if sys.platform == "darwin":
            system_dir = os.path.expanduser("~/Library/Caches/mcp_nixos")
        else:
            system_dir = os.path.expanduser("~/.cache/mcp_nixos")

        # If the system dir exists, it shouldn't have any new files from our test
        if os.path.exists(system_dir):
            test_files = [f for f in os.listdir(system_dir) if "test" in f.lower()]
            assert len(test_files) == 0, f"System cache directory {system_dir} contains test files: {test_files}"
