"""Tests for cross-platform cache directory management."""

import os
import pathlib
import sys
import tempfile
import threading
import time
from unittest import mock

import pytest

# By default mark as integration tests
pytestmark = pytest.mark.integration

from mcp_nixos.cache.html_cache import HTMLCache
from mcp_nixos.clients.home_manager_client import HomeManagerClient
from mcp_nixos.clients.html_client import HTMLClient
from mcp_nixos.utils.cache_helpers import ensure_cache_dir, get_default_cache_dir


@pytest.mark.integration
class TestCrossplatformIntegration:
    """Integration tests for cross-platform HTML caching."""

    def test_cache_platform_specific_paths(self):
        """Test that appropriate paths are returned for each platform."""

        # Helper function to verify path components regardless of platform
        def verify_path_components(actual_path, expected_components):
            """Verify path contains expected components in a platform-agnostic way."""
            path_parts = pathlib.Path(actual_path).parts
            for component in expected_components:
                assert component in path_parts, f"Path {actual_path} missing component '{component}'"

        # Linux
        with mock.patch("sys.platform", "linux"):
            with mock.patch.dict(os.environ, {"XDG_CACHE_HOME": "/xdg/cache"}):
                cache_dir = get_default_cache_dir()
                verify_path_components(cache_dir, ["xdg", "cache", "mcp_nixos"])
                # For Linux, we can still safely check the exact path
                assert str(pathlib.Path(cache_dir)) == str(pathlib.Path("/xdg/cache/mcp_nixos"))

        # macOS
        with mock.patch("sys.platform", "darwin"):
            with mock.patch("pathlib.Path.home", return_value=pathlib.Path("/Users/test")):
                cache_dir = get_default_cache_dir()
                verify_path_components(cache_dir, ["Users", "test", "Library", "Caches", "mcp_nixos"])
                # For macOS, we can still safely check the exact path
                assert str(pathlib.Path(cache_dir)) == str(pathlib.Path("/Users/test/Library/Caches/mcp_nixos"))

        # Windows
        with mock.patch("sys.platform", "win32"):
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": r"C:\Users\test\AppData\Local"}):
                cache_dir = get_default_cache_dir()
                # For Windows, we need to be careful with path comparison
                # Verify key components expected in the path
                path_obj = pathlib.Path(cache_dir)

                # Check the path ends correctly
                if sys.platform == "win32":
                    # On Windows, pathlib correctly parses Windows paths
                    assert path_obj.parts[-1] == "Cache"
                    assert path_obj.parts[-2] == "mcp_nixos"
                else:
                    # On non-Windows platforms, manually check path endings
                    assert cache_dir.endswith(os.path.join("mcp_nixos", "Cache"))

                # These checks work cross-platform
                assert "mcp_nixos" in str(path_obj)
                assert "Cache" in str(path_obj)
                assert "AppData" in str(path_obj)
                assert "Local" in str(path_obj)

    def test_html_client_environment_ttl(self):
        """Test that HTMLClient respects environment TTL setting."""
        # Set environment variable for TTL
        with mock.patch.dict(os.environ, {"MCP_NIXOS_CACHE_TTL": "7200"}):  # 2 hours
            client = HomeManagerClient()
            assert client.cache_ttl == 7200
            # Check if cache is not None before accessing ttl
            assert client.html_client.cache is not None
            assert client.html_client.cache.ttl == 7200

    def test_home_manager_client_html_caching(self):
        """Test that HomeManagerClient correctly uses HTML caching."""
        # Setup
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a client with the temp directory as cache dir
            with mock.patch.dict(os.environ, {"MCP_NIXOS_CACHE_DIR": temp_dir}):
                client = HomeManagerClient()

                # Mock HTML client's fetch method directly
                # (because we need to isolate the test from requests.get)
                original_fetch = client.html_client.fetch
                fetch_call_count = {"web": 0, "cache": 0}

                def mock_fetch(url, force_refresh=False):
                    if force_refresh or url not in getattr(mock_fetch, "cache", {}):
                        # Simulate a web request
                        fetch_call_count["web"] += 1
                        content = "<html><body>Test Content</body></html>"
                        if not hasattr(mock_fetch, "cache"):
                            mock_fetch.cache = {}
                        mock_fetch.cache[url] = content
                        return content, {"from_cache": False, "success": True}
                    else:
                        # Simulate a cache hit
                        fetch_call_count["cache"] += 1
                        return mock_fetch.cache[url], {"from_cache": True, "success": True, "cache_hit": True}

                # Apply mock
                client.html_client.fetch = mock_fetch

                try:
                    # First call should hit the web
                    url = client.hm_urls["options"]
                    html = client.fetch_url(url)
                    assert html == "<html><body>Test Content</body></html>"
                    assert fetch_call_count["web"] == 1
                    assert fetch_call_count["cache"] == 0

                    # Second call should use cache
                    html2 = client.fetch_url(url)
                    assert html2 == "<html><body>Test Content</body></html>"
                    assert fetch_call_count["web"] == 1  # No change
                    assert fetch_call_count["cache"] == 1  # Increased

                    # Force refresh should bypass cache
                    html3 = client.fetch_url(url, force_refresh=True)
                    assert html3 == "<html><body>Test Content</body></html>"
                    assert fetch_call_count["web"] == 2  # Increased
                    assert fetch_call_count["cache"] == 1  # No change
                finally:
                    # Restore original method
                    client.html_client.fetch = original_fetch

    @pytest.mark.skipif(sys.platform == "win32", reason="Test relies on Unix permissions")
    def test_cache_dir_permissions(self):
        """Test that cache directories are created with correct permissions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = os.path.join(temp_dir, "cache_test")
            path = ensure_cache_dir(test_dir)

            # Check the directory was created
            assert os.path.isdir(path)

            # Check permissions on Unix systems
            if sys.platform != "win32":
                mode = os.stat(path).st_mode & 0o777  # Get permission bits
                assert mode == 0o700  # Owner only

    def test_integration_with_default_cache_dir(self):
        """Test that default cache directory is correctly created."""
        # Create a client that would use the default dir
        with mock.patch("mcp_nixos.cache.html_cache.init_cache_storage") as mock_init:
            mock_init.return_value = {"cache_dir": "/fake/path", "ttl": 86400, "initialized": True}

            HTMLClient()
            # Check that it was initialized with the mocked init_cache_storage
            mock_init.assert_called_once()


class TestMultithreadingCache:
    """Tests for cache behavior in multithreaded scenarios."""

    def test_concurrent_cache_access(self):
        """Test that cache can be safely accessed from multiple threads."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create cache
            cache = HTMLCache(cache_dir=temp_dir)
            results = []
            errors = []

            # Function to run in threads
            def cache_operation(thread_id):
                try:
                    url = f"https://example.com/thread{thread_id}"
                    content = f"<html>Content for thread {thread_id}</html>"

                    # Set to cache
                    cache.set(url, content)

                    # Small delay to increase chance of conflicts
                    time.sleep(0.01)

                    # Get from cache
                    cached, _ = cache.get(url)

                    # Record result
                    results.append((thread_id, cached == content))
                except Exception as e:
                    errors.append(f"Thread {thread_id}: {str(e)}")

            # Start multiple threads
            threads = []
            for i in range(10):
                thread = threading.Thread(target=cache_operation, args=(i,))
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # Check results
            assert len(errors) == 0, f"Thread errors: {', '.join(errors)}"
            assert len(results) == 10, "Not all threads completed"
            assert all(success for _, success in results), "Cache operations failed"

            # Check cache stats are correct
            stats = cache.get_stats()
            assert stats["hits"] == 10
            assert stats["writes"] == 10

            # With our enhanced implementation, we should have both content files and metadata files
            # So we should have 20 files in total (10 content + 10 metadata)
            assert stats["file_count"] == 20, f"Expected 20 files (10 content + 10 metadata), got {stats['file_count']}"
            # Ensure we have 10 HTML files (the content files)
            assert stats["html_count"] == 10, f"Expected 10 HTML files, got {stats['html_count']}"
            # We should also have 10 metadata files
            assert stats["meta_count"] == 10, f"Expected 10 metadata files, got {stats['meta_count']}"
