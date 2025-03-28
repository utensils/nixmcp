"""Unit tests for HTML cache implementation."""

import os
import tempfile
import time
import pathlib
import json
from collections import defaultdict
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
        self.test_key = "test_data_key"
        self.test_data = {"name": "Test Data", "values": [1, 2, 3], "nested": {"key": "value"}}
        self.test_binary_data = {"set": set(["a", "b", "c"]), "defaultdict": defaultdict(list, {"key1": [1, 2, 3]})}

    def teardown_method(self):
        """Tear down test fixtures."""
        self.temp_dir.cleanup()

    def test_init(self):
        """Test HTMLCache initialization."""
        assert str(self.cache.cache_dir) == self.cache_dir  # Convert pathlib.Path to string
        assert self.cache.ttl == 3600
        assert self.cache.stats["hits"] == 0
        assert self.cache.stats["misses"] == 0
        assert self.cache.stats["data_hits"] == 0
        assert self.cache.stats["data_misses"] == 0

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

    def test_data_cache_path_generation(self):
        """Test key to data cache path conversion."""
        cache_path = self.cache._get_data_cache_path(self.test_key)
        assert str(cache_path).startswith(self.cache_dir)
        assert str(cache_path).endswith(".data.json")

        binary_cache_path = self.cache._get_binary_data_cache_path(self.test_key)
        assert str(binary_cache_path).startswith(self.cache_dir)
        assert str(binary_cache_path).endswith(".data.pickle")

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

    def test_set_and_get_data(self):
        """Test setting and retrieving structured data from cache."""
        # Set data in cache
        set_result = self.cache.set_data(self.test_key, self.test_data)
        assert set_result["stored"] is True
        assert self.cache.stats["data_writes"] == 1

        # Get data from cache
        data, metadata = self.cache.get_data(self.test_key)
        assert data == self.test_data
        assert metadata["cache_hit"] is True
        assert self.cache.stats["data_hits"] == 1

        # Verify data was actually written to disk
        data_path = self.cache._get_data_cache_path(self.test_key)
        assert data_path.exists()
        with open(data_path, "r") as f:
            stored_data = json.load(f)
        assert stored_data == self.test_data

    def test_set_and_get_binary_data(self):
        """Test setting and retrieving binary data from cache."""
        # Set binary data in cache
        set_result = self.cache.set_binary_data(self.test_key, self.test_binary_data)
        assert set_result["stored"] is True
        assert self.cache.stats["data_writes"] == 1

        # Get binary data from cache
        data, metadata = self.cache.get_binary_data(self.test_key)
        assert isinstance(data, dict)
        assert isinstance(data["set"], set)
        assert isinstance(data["defaultdict"], defaultdict)
        assert metadata["cache_hit"] is True
        assert self.cache.stats["data_hits"] == 1

        # Verify data was actually written to disk
        data_path = self.cache._get_binary_data_cache_path(self.test_key)
        assert data_path.exists()

    def test_get_expired(self):
        """Test getting expired content from cache."""
        # Create cache with very short TTL
        short_ttl_cache = HTMLCache(cache_dir=self.cache_dir, ttl=1)

        # Set content
        short_ttl_cache.set(self.test_url, self.test_content)
        short_ttl_cache.set_data(self.test_key, self.test_data)

        # Wait for content to expire
        time.sleep(1.1)

        # Get content (should be a miss)
        content, metadata = short_ttl_cache.get(self.test_url)
        assert content is None
        assert metadata["expired"] is True
        assert metadata["cache_hit"] is False
        assert short_ttl_cache.stats["misses"] == 1
        assert short_ttl_cache.stats["hits"] == 0

        # Get data (should be a miss)
        data, data_metadata = short_ttl_cache.get_data(self.test_key)
        assert data is None
        assert data_metadata["expired"] is True
        assert data_metadata["cache_hit"] is False
        assert short_ttl_cache.stats["data_misses"] == 1
        assert short_ttl_cache.stats["data_hits"] == 0

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

    def test_invalidate_data(self):
        """Test invalidation of data cache."""
        # Set data in cache
        self.cache.set_data(self.test_key, self.test_data)
        self.cache.set_binary_data(self.test_key, self.test_binary_data)

        # Verify data exists
        data, _ = self.cache.get_data(self.test_key)
        assert data == self.test_data

        binary_data, _ = self.cache.get_binary_data(self.test_key)
        assert binary_data is not None

        # Invalidate the data cache
        invalidate_result = self.cache.invalidate_data(self.test_key)
        assert invalidate_result["invalidated"] is True
        assert invalidate_result["binary_invalidated"] is True

        # Data should no longer be in cache
        data, metadata = self.cache.get_data(self.test_key)
        assert data is None
        assert metadata["cache_hit"] is False

        binary_data, binary_metadata = self.cache.get_binary_data(self.test_key)
        assert binary_data is None
        assert binary_metadata["cache_hit"] is False

    def test_clear(self):
        """Test clearing all content from cache."""
        # Set multiple items in cache
        self.cache.set(self.test_url, self.test_content)
        self.cache.set("https://example.com/other", "Other content")
        self.cache.set_data(self.test_key, self.test_data)
        self.cache.set_binary_data(self.test_key, self.test_binary_data)

        # Clear the cache
        clear_result = self.cache.clear()
        assert clear_result["cleared"] is True
        assert clear_result["files_removed"] == 4  # 2 HTML, 1 JSON, 1 pickle

        # Cache should be empty
        content, _ = self.cache.get(self.test_url)
        assert content is None

        data, _ = self.cache.get_data(self.test_key)
        assert data is None

        binary_data, _ = self.cache.get_binary_data(self.test_key)
        assert binary_data is None

    def test_get_stats(self):
        """Test retrieving cache statistics."""
        # Perform some operations to generate stats
        self.cache.get(self.test_url)  # Miss
        self.cache.set(self.test_url, self.test_content)
        self.cache.get(self.test_url)  # Hit

        self.cache.get_data(self.test_key)  # Miss
        self.cache.set_data(self.test_key, self.test_data)
        self.cache.get_data(self.test_key)  # Hit

        self.cache.get_binary_data(self.test_key)  # Miss
        self.cache.set_binary_data(self.test_key, self.test_binary_data)
        self.cache.get_binary_data(self.test_key)  # Hit

        # Get stats
        stats = self.cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_ratio"] == 0.5
        assert stats["data_hits"] == 2
        assert stats["data_misses"] == 2
        assert stats["data_hit_ratio"] == 0.5
        assert stats["writes"] == 1
        assert stats["data_writes"] == 2
        assert stats["cache_dir"] == str(self.cache.cache_dir)
        assert stats["file_count"] == 3
        assert stats["html_count"] == 1
        assert stats["data_count"] == 1
        assert stats["binary_data_count"] == 1
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

        # Test error during data get
        with mock.patch("pathlib.Path.exists", return_value=True):
            with mock.patch("pathlib.Path.read_text", side_effect=IOError("Read error")):
                data, metadata = self.cache.get_data(self.test_key)
                assert data is None
                assert "error" in metadata
                assert self.cache.stats["errors"] == 3

        # Test error during data set
        with mock.patch("pathlib.Path.write_text", side_effect=IOError("Write error")):
            set_result = self.cache.set_data(self.test_key, self.test_data)
            assert set_result["stored"] is False
            assert "error" in set_result
            assert self.cache.stats["errors"] == 4

        # Test error during binary data operations
        with mock.patch("builtins.open", mock.mock_open()) as m:
            m.side_effect = IOError("Pickle error")
            set_result = self.cache.set_binary_data(self.test_key, self.test_binary_data)
            assert set_result["stored"] is False
            assert "error" in set_result
