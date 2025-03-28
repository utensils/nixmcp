"""Tests for cache TTL expiration behavior across different components."""

import time
import pytest
import tempfile
from unittest.mock import MagicMock, patch

from nixmcp.cache.html_cache import HTMLCache
from nixmcp.clients.html_client import HTMLClient


@pytest.fixture
def real_cache_dir():
    """Create a temporary directory for a real cache."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.mark.asyncio
async def test_html_cache_ttl_expiration(real_cache_dir):
    """
    Test that HTMLCache properly respects TTL expiration.
    """
    # Create a cache with a very short TTL (1 second)
    short_ttl = 1
    html_cache = HTMLCache(cache_dir=real_cache_dir, ttl=short_ttl)

    # Create test data
    test_url = "https://example.com/test"
    test_content = "<html><body>Test content</body></html>"
    test_key = "test_data"
    test_data = {"key": "value", "timestamp": time.time()}

    # Set content in cache
    html_cache.set(test_url, test_content)
    html_cache.set_data(test_key, test_data)

    # Verify content is in cache
    cached_content, metadata = html_cache.get(test_url)
    assert cached_content == test_content
    assert metadata["cache_hit"] is True

    cached_data, data_metadata = html_cache.get_data(test_key)
    assert cached_data == test_data
    assert data_metadata["cache_hit"] is True

    # Wait for TTL to expire
    time.sleep(short_ttl + 0.5)

    # Verify content is expired
    expired_content, expired_metadata = html_cache.get(test_url)
    assert expired_content is None
    assert expired_metadata["expired"] is True

    expired_data, expired_data_metadata = html_cache.get_data(test_key)
    assert expired_data is None
    assert expired_data_metadata["expired"] is True


@pytest.mark.asyncio
async def test_html_client_ttl_expiration(real_cache_dir):
    """
    Test that HTMLClient properly reloads content when cache TTL expires.
    """
    # Create a cache with a very short TTL (1 second)
    short_ttl = 1

    # Create a real HTMLClient with short TTL
    html_client = HTMLClient(cache_dir=real_cache_dir, ttl=short_ttl)

    # Test URL and content
    test_url = "https://example.com/test"
    test_content1 = "<html><body>Original content</body></html>"
    test_content2 = "<html><body>Updated content</body></html>"

    # Mock the requests.get function
    with patch("requests.get") as mock_get:
        # Setup mock to return different responses
        mock_response1 = MagicMock()
        mock_response1.text = test_content1
        mock_response1.status_code = 200
        mock_response1.raise_for_status = MagicMock()

        mock_response2 = MagicMock()
        mock_response2.text = test_content2
        mock_response2.status_code = 200
        mock_response2.raise_for_status = MagicMock()

        # Return different responses for successive calls
        mock_get.side_effect = [mock_response1, mock_response2]

        # First fetch - should get from web
        content1, metadata1 = html_client.fetch(test_url)
        assert content1 == test_content1
        assert metadata1["from_cache"] is False

        # Immediate second fetch - should use cache
        content2, metadata2 = html_client.fetch(test_url)
        assert content2 == test_content1
        assert metadata2["from_cache"] is True

        # Wait for cache to expire
        time.sleep(short_ttl + 0.5)

        # Fetch after expiration - should get from web again
        content3, metadata3 = html_client.fetch(test_url)
        assert content3 == test_content2
        assert metadata3["from_cache"] is False

        # Verify mock_get was called twice
        assert mock_get.call_count == 2


# Note: We don't need a separate test for HomeManagerClient cache TTL behavior
# because the underlying components (HTMLCache and HTMLClient) are already tested,
# and those tests cover the core cache TTL expiration functionality.
