"""Test Darwin client serialization in cache."""

import os
import shutil
import tempfile
import pytest
from unittest.mock import AsyncMock

from nixmcp.clients.darwin.darwin_client import DarwinClient


@pytest.fixture
def temp_cache_dir():
    """Create a temporary directory for cache testing."""
    temp_dir = tempfile.mkdtemp(prefix="nixmcp_test_cache_")
    old_cache_dir = os.environ.get("NIXMCP_CACHE_DIR")

    # Set environment variable to use our temp dir
    os.environ["NIXMCP_CACHE_DIR"] = temp_dir

    yield temp_dir

    # Cleanup
    if old_cache_dir:
        os.environ["NIXMCP_CACHE_DIR"] = old_cache_dir
    else:
        del os.environ["NIXMCP_CACHE_DIR"]

    shutil.rmtree(temp_dir)


@pytest.mark.asyncio
async def test_darwin_cache_serialization_integration(temp_cache_dir):
    """Test Darwin client's cache serialization with real filesystem integration."""
    # Create a Darwin client with a real filesystem cache
    client = DarwinClient()

    # Mock the fetch_url method to return a simple HTML snippet
    client.fetch_url = AsyncMock(
        return_value="""
    <html>
    <body>
        <dl class="variablelist">
            <dt>
                <a id="opt-test.option"></a>
                <code class="option">test.option</code>
            </dt>
            <dd>
                <p>Test option description.</p>
                <p><span class="emphasis"><em>Type:</em></span> string</p>
                <p><span class="emphasis"><em>Default:</em></span> default value</p>
            </dd>
        </dl>
    </body>
    </html>
    """
    )

    # Load options (this will parse the mock HTML and create the cache)
    await client.load_options()

    # Verify we have the parsed option
    assert "test.option" in client.options

    # Create a new client that should load from cache
    new_client = DarwinClient()
    # Mock fetch_url to verify it's not called
    new_client.fetch_url = AsyncMock()

    # Load options (should load from cache, not call fetch_url)
    await new_client.load_options()

    # Verify data was loaded correctly from cache
    assert "test.option" in new_client.options
    # The parser may combine all text content into the description, so just check that the core info is there
    assert "Test option description" in new_client.options["test.option"].description
    # Just make sure some basic properties are included
    assert "string" in new_client.options["test.option"].type
    assert "default value" in new_client.options["test.option"].default

    # Verify fetch_url wasn't called
    new_client.fetch_url.assert_not_called()
