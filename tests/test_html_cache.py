"""Unit tests for HTML cache implementation."""

import os
import tempfile
import time
import pathlib
from unittest import mock

from nixmcp.cache.html_cache import HTMLCache


class TestHTMLCache:
    """Tests for the HTMLCache class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_dir = self.temp_dir.name
        self.cache = HTMLCache(cache_dir=self.cache_dir, ttl=3600)
        self.test_url = "https://example.com/test"
        self.test_content = "<html><body>Test Content</body></html>"

    def teardown_method(self):
        """Tear down test fixtures."""
        self.temp_dir.cleanup()

    def test_init(self):
        """Test HTMLCache initialization."""
        assert str(self.cache.cache_dir) == self.cache_dir  # Convert pathlib.Path to string
        assert self.cache.ttl == 3600
        assert self.cache.stats["hits"] == 0
        assert self.cache.stats["misses"] == 0

    def test_cache_path_generation(self):
        """Test URL to cache path conversion."""
        cache_path = self.cache._get_cache_path(self.test_url)
        assert str(cache_path).startswith(self.cache_dir)
        assert str(cache_path).endswith(".html")

        # Same URL should generate same path
        cache_path2 = self.cache._get_cache_path(self.test_url)
        assert cache_path == cache_path2

        # Different URLs should generate different paths
        different_path = self.cache._get_cache_path("https://example.org/other")
        assert cache_path != different_path

    def test_is_expired(self):
        """Test cache expiration checking."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        # Should be fresh
        cache = HTMLCache(ttl=3600)  # 1 hour TTL
        assert not cache._is_expired(pathlib.Path(temp_path))

        # Should be expired
        cache = HTMLCache(ttl=1)  # 1 second TTL
        time.sleep(1.1)  # Wait for expiration
        assert cache._is_expired(pathlib.Path(temp_path))

        # Non-existent file should be considered expired
        os.unlink(temp_path)
        assert cache._is_expired(pathlib.Path(temp_path))

    def test_get_miss(self):
        """Test cache miss when content is not in cache."""
        content, metadata = self.cache.get(self.test_url)
        assert content is None
        assert metadata["cache_hit"] is False
        assert self.cache.stats["misses"] == 1
        assert self.cache.stats["hits"] == 0

    def test_set_and_get(self):
        """Test setting and retrieving content from cache."""
        # Set content in cache
        set_result = self.cache.set(self.test_url, self.test_content)
        assert set_result["stored"] is True
        assert self.cache.stats["writes"] == 1

        # Get content from cache
        content, metadata = self.cache.get(self.test_url)
        assert content == self.test_content
        assert metadata["cache_hit"] is True
        assert self.cache.stats["hits"] == 1

    def test_get_expired(self):
        """Test getting expired content from cache."""
        # Create cache with very short TTL
        short_ttl_cache = HTMLCache(cache_dir=self.cache_dir, ttl=1)

        # Set content
        short_ttl_cache.set(self.test_url, self.test_content)

        # Wait for content to expire
        time.sleep(1.1)

        # Get content (should be a miss)
        content, metadata = short_ttl_cache.get(self.test_url)
        assert content is None
        assert metadata["expired"] is True
        assert metadata["cache_hit"] is False
        assert short_ttl_cache.stats["misses"] == 1
        assert short_ttl_cache.stats["hits"] == 0

    def test_invalidate(self):
        """Test cache invalidation for a specific URL."""
        # Set content in cache
        self.cache.set(self.test_url, self.test_content)

        # Verify content exists
        content, _ = self.cache.get(self.test_url)
        assert content == self.test_content

        # Invalidate the cache for this URL
        invalidate_result = self.cache.invalidate(self.test_url)
        assert invalidate_result["invalidated"] is True

        # Content should no longer be in cache
        content, metadata = self.cache.get(self.test_url)
        assert content is None
        assert metadata["cache_hit"] is False

        # Invalidating non-existent URL should not raise error
        result = self.cache.invalidate("https://example.com/nonexistent")
        assert result["invalidated"] is False

    def test_clear(self):
        """Test clearing all content from cache."""
        # Set multiple items in cache
        self.cache.set(self.test_url, self.test_content)
        self.cache.set("https://example.com/other", "Other content")

        # Clear the cache
        clear_result = self.cache.clear()
        assert clear_result["cleared"] is True
        assert clear_result["files_removed"] == 2

        # Cache should be empty
        content, _ = self.cache.get(self.test_url)
        assert content is None

    def test_get_stats(self):
        """Test retrieving cache statistics."""
        # Perform some operations to generate stats
        self.cache.get(self.test_url)  # Miss
        self.cache.set(self.test_url, self.test_content)
        self.cache.get(self.test_url)  # Hit

        # Get stats
        stats = self.cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_ratio"] == 0.5
        assert stats["writes"] == 1
        assert stats["cache_dir"] == str(self.cache.cache_dir)
        assert stats["file_count"] == 1
        assert stats["cache_size_bytes"] > 0

    def test_error_handling(self):
        """Test error handling during cache operations."""
        # Test error during get
        with mock.patch("pathlib.Path.exists", return_value=True):
            with mock.patch("pathlib.Path.read_text", side_effect=IOError("Read error")):
                content, metadata = self.cache.get(self.test_url)
                assert content is None
                assert "error" in metadata
                assert self.cache.stats["errors"] == 1

        # Test error during set
        with mock.patch("pathlib.Path.write_text", side_effect=IOError("Write error")):
            set_result = self.cache.set(self.test_url, self.test_content)
            assert set_result["stored"] is False
            assert "error" in set_result
            assert self.cache.stats["errors"] == 2
