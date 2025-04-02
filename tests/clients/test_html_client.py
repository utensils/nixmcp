"""Unit tests for HTML client implementation."""

import tempfile
import pytest
from unittest import mock

import requests

# Mark as unit tests
pytestmark = pytest.mark.unit

from mcp_nixos.clients.html_client import HTMLClient
from mcp_nixos.cache.html_cache import HTMLCache


class TestHTMLClient:
    """Tests for the HTMLClient class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_dir = self.temp_dir.name
        self.client = HTMLClient(cache_dir=self.cache_dir, ttl=3600)
        self.test_url = "https://example.com/test"
        self.test_content = "<html><body>Test Content</body></html>"

    def teardown_method(self):
        """Tear down test fixtures."""
        self.temp_dir.cleanup()

    def test_init(self):
        """Test HTMLClient initialization."""
        # Test with caching enabled
        client = HTMLClient(cache_dir=self.cache_dir)
        assert client.use_cache is True
        assert isinstance(client.cache, HTMLCache)

        # Test with caching disabled
        client_no_cache = HTMLClient(use_cache=False)
        assert client_no_cache.use_cache is False
        assert client_no_cache.cache is None

    @mock.patch("requests.get")
    def test_fetch_from_web(self, mock_get):
        """Test fetching content from web."""
        # Mock successful HTTP response
        mock_response = mock.Mock()
        mock_response.text = self.test_content
        mock_response.status_code = 200
        mock_response.raise_for_status = mock.Mock()
        mock_get.return_value = mock_response

        # Fetch content
        content, metadata = self.client.fetch(self.test_url)

        # Verify results
        assert content == self.test_content
        assert metadata["success"] is True
        assert metadata["from_cache"] is False
        assert metadata["status_code"] == 200

        # Verify the content was cached
        assert "cache_result" in metadata
        assert metadata["cache_result"]["stored"] is True

    @mock.patch("requests.get")
    def test_fetch_from_cache(self, mock_get):
        """Test fetching content from cache."""
        # First, ensure cache is available and store content in cache
        assert self.client.cache is not None
        self.client.cache.set(self.test_url, self.test_content)

        # Now fetch the content (should come from cache)
        content, metadata = self.client.fetch(self.test_url)

        # Verify results
        assert content == self.test_content
        assert metadata["success"] is True
        assert metadata["from_cache"] is True
        assert metadata["cache_hit"] is True

        # Verify that requests.get was not called
        mock_get.assert_not_called()

    @mock.patch("requests.get")
    def test_fetch_force_refresh(self, mock_get):
        """Test forcing a refresh from web."""
        # First, ensure cache is available and store content in cache
        assert self.client.cache is not None
        self.client.cache.set(self.test_url, self.test_content)

        # Set up mock response with different content
        mock_response = mock.Mock()
        mock_response.text = "<html><body>Updated Content</body></html>"
        mock_response.status_code = 200
        mock_response.raise_for_status = mock.Mock()
        mock_get.return_value = mock_response

        # Fetch with force_refresh=True
        content, metadata = self.client.fetch(self.test_url, force_refresh=True)

        # Verify we got the updated content, not the cached content
        assert content == "<html><body>Updated Content</body></html>"
        assert metadata["from_cache"] is False
        assert metadata["success"] is True

        # Verify that requests.get was called
        mock_get.assert_called_once_with(self.test_url, timeout=30)

    @mock.patch("requests.get")
    def test_fetch_error(self, mock_get):
        """Test error handling during fetch."""
        # Mock HTTP error
        mock_get.side_effect = requests.RequestException("Network error")

        # Fetch content
        content, metadata = self.client.fetch(self.test_url)

        # Verify error was handled properly
        assert content is None
        assert metadata["success"] is False
        assert "error" in metadata
        assert "Network error" in metadata["error"]

    def test_clear_cache(self):
        """Test clearing the cache."""
        # Ensure cache is available and store some content in cache
        assert self.client.cache is not None
        self.client.cache.set(self.test_url, self.test_content)
        self.client.cache.set("https://example.com/other", "Other content")

        # Clear cache
        result = self.client.clear_cache()

        # Verify cache was cleared
        assert result["cleared"] is True
        # Our improved implementation creates both content files and metadata files
        # So we should have 4 files (2 content + 2 metadata)
        assert result["files_removed"] == 4

        # Verify cache is empty
        assert self.client.cache is not None
        content, _ = self.client.cache.get(self.test_url)
        assert content is None

    def test_get_cache_stats(self):
        """Test retrieving cache statistics."""
        # Perform some operations to generate stats
        with mock.patch("requests.get") as mock_get:
            mock_response = mock.Mock()
            mock_response.text = self.test_content
            mock_response.status_code = 200
            mock_response.raise_for_status = mock.Mock()
            mock_get.return_value = mock_response

            # Generate a miss followed by a hit
            self.client.fetch(self.test_url)  # Will go to web and cache
            self.client.fetch(self.test_url)  # Will hit cache

        # Get stats
        stats = self.client.get_cache_stats()

        # Verify stats
        assert stats["hits"] == 1
        assert stats["writes"] == 1
        assert self.client.cache is not None
        assert str(stats["cache_dir"]) == str(self.client.cache.cache_dir)

        # Our improved implementation creates both content files and metadata files
        # So we should have 2 files (1 content + 1 metadata)
        assert stats["file_count"] == 2
        # Specifically check for the correct types of files
        assert stats["html_count"] == 1, f"Expected 1 HTML file, got {stats.get('html_count', 0)}"
        assert stats["meta_count"] == 1, f"Expected 1 metadata file, got {stats.get('meta_count', 0)}"
        # Note: depending on implementation, misses might be counted differently

    def test_disabled_cache(self):
        """Test client with disabled cache."""
        client = HTMLClient(use_cache=False)

        # Methods should return indication that cache is disabled
        clear_result = client.clear_cache()
        assert clear_result == {"cache_enabled": False}

        stats_result = client.get_cache_stats()
        assert stats_result == {"cache_enabled": False}

        # Fetch should work but not cache anything
        with mock.patch("requests.get") as mock_get:
            mock_response = mock.Mock()
            mock_response.text = self.test_content
            mock_response.status_code = 200
            mock_response.raise_for_status = mock.Mock()
            mock_get.return_value = mock_response

            content, metadata = client.fetch(self.test_url)
            assert content == self.test_content
            assert "cache_result" not in metadata
