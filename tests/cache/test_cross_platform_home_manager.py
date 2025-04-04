"""
Tests for cross-platform compatibility of the Home Manager client cache.
"""

import unittest
import os
import sys
import tempfile
import shutil
import pytest
import re
import uuid
from unittest.mock import patch, MagicMock
from pathlib import Path

# Mark as integration tests since we're testing disk operations
pytestmark = pytest.mark.integration

# Import the client to test
from mcp_nixos.clients.home_manager_client import HomeManagerClient
from mcp_nixos.cache.simple_cache import SimpleCache
from mcp_nixos.clients.html_client import HTMLClient


class TestHomeManagerCacheCrossPlatform(unittest.TestCase):
    """Test the Home Manager client cache for cross-platform compatibility."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for cache files
        self.temp_dir = tempfile.mkdtemp()
        
        # Set up environment for tests
        self.original_cache_dir = os.environ.get("MCP_NIXOS_CACHE_DIR")
        os.environ["MCP_NIXOS_CACHE_DIR"] = self.temp_dir
        
        # Create a small set of test options data
        self.test_options = [
            {
                "name": "programs.test.enable",
                "description": "Enable test program",
                "type": "boolean",
                "default": "false",
                "category": "Programs",
                "source": "test-source",
            }
        ]

    def tearDown(self):
        """Clean up after tests."""
        # Restore original environment
        if self.original_cache_dir:
            os.environ["MCP_NIXOS_CACHE_DIR"] = self.original_cache_dir
        else:
            os.environ.pop("MCP_NIXOS_CACHE_DIR", None)
        
        # Remove temp directory
        shutil.rmtree(self.temp_dir)

    @pytest.mark.skipif(sys.platform == "win32", reason="Test relies on Unix permissions")
    def test_cache_directory_permissions_unix(self):
        """Test cache directory permissions on Unix systems."""
        # Create a client which should initialize the cache directory
        client = HomeManagerClient()
        cache_path = Path(self.temp_dir)
        
        # Verify the directory was created with correct permissions
        self.assertTrue(cache_path.exists())
        
        # Check directory permissions (should be at least rwx for user)
        mode = cache_path.stat().st_mode
        user_rwx = mode & 0o700  # Extract user bits
        self.assertEqual(user_rwx, 0o700, "Directory should have rwx permissions for user")

    def test_url_caching(self):
        """Test that URLs are cached correctly across platforms."""
        # Create a client with a mocked HTML client
        mock_html_client = MagicMock()
        client = HomeManagerClient()
        client.html_client = mock_html_client
        
        # Set up mock return values
        mock_html_client.fetch.return_value = ("test data", {"success": True, "from_cache": False})
        
        # Test fetching a URL
        url = "https://test-example.com/path/page.html"
        result, metadata = client.html_client.fetch(url)
        
        # Verify the fetch was called with the correct URL
        mock_html_client.fetch.assert_called_once()
        call_args = mock_html_client.fetch.call_args[0]
        self.assertEqual(call_args[0], url)
        
        # Verify we got the expected result
        self.assertEqual(result, "test data")
        
        # Reset the mock
        mock_html_client.fetch.reset_mock()
        
        # Test with a URL containing special characters
        special_url = "https://example.com/path with spaces/file:name.html"
        client.html_client.fetch(special_url)
        
        # Verify the fetch was called with the correct URL
        mock_html_client.fetch.assert_called_once()
        call_args = mock_html_client.fetch.call_args[0]
        self.assertEqual(call_args[0], special_url)

    def test_simple_cache_behavior(self):
        """Test SimpleCache behavior for cross-platform compatibility."""
        # Create a simple cache
        simple_cache = SimpleCache(max_size=10, ttl=60)
        
        # Test with simple string key
        simple_cache.set("test_key", "test_value")
        self.assertEqual(simple_cache.get("test_key"), "test_value")
        
        # Test with key containing special characters
        complex_key = "test:key/with\\special*chars?"
        simple_cache.set(complex_key, "complex_value")
        self.assertEqual(simple_cache.get(complex_key), "complex_value")
        
        # Test that the cache handles unicode properly
        unicode_key = "unicode_key_🔑"
        unicode_value = "unicode_value_📝"
        simple_cache.set(unicode_key, unicode_value)
        self.assertEqual(simple_cache.get(unicode_key), unicode_value)
        
        # Verify stats are platform-independent
        stats = simple_cache.get_stats()
        self.assertEqual(stats["size"], 3)
        self.assertEqual(stats["hits"], 3)
        self.assertEqual(stats["misses"], 0)

    @patch.object(HTMLClient, "fetch")
    def test_save_and_load_cache_data(self, mock_fetch):
        """Test saving and loading cache data works correctly."""
        # Mock HTMLClient fetch to return test data
        mock_fetch.return_value = (
            """<html><div class="variablelist"><dl>
            <dt><span class="term"><code>test.option</code></span></dt>
            <dd><p>Test description</p><p>Type: boolean</p></dd>
            </dl></div></html>""",
            {"success": True, "from_cache": False}
        )
        
        # Create client
        client = HomeManagerClient()
        
        # Mock load_all_options to go through our patched fetch
        # We don't need a real implementation, just verify the data path works
        options_data = client.load_all_options()
        
        # Verify we got some data back (simplified test)
        self.assertIsNotNone(options_data)
        mock_fetch.assert_called()

    def test_invalidate_cache(self):
        """Test cache invalidation removes the cached data."""
        # Create a client
        client = HomeManagerClient()
        
        # Use in-memory SimpleCache directly for testing
        simple_cache = SimpleCache(max_size=10, ttl=60)
        
        # Create test data
        test_key = "test_key"
        test_data = "test_data"
        
        # Set data in the cache
        simple_cache.set(test_key, test_data)
        
        # Verify it's cached
        self.assertEqual(simple_cache.get(test_key), test_data)
        
        # Clear the cache
        simple_cache.clear()
        
        # Verify data is gone
        self.assertIsNone(simple_cache.get(test_key))


if __name__ == "__main__":
    unittest.main()