"""Tests for the Darwin client filesystem caching."""

import time
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from nixmcp.clients.darwin.darwin_client import DarwinClient, DarwinOption
from nixmcp.clients.html_client import HTMLClient
from nixmcp.cache.html_cache import HTMLCache


@pytest.fixture
def mock_html_client():
    """Create a mock HTML client with filesystem caching capabilities."""
    client = MagicMock(spec=HTMLClient)

    # Mock the cache
    cache = MagicMock(spec=HTMLCache)
    client.cache = cache

    # Setup cache get_data and get_binary_data to return cache misses
    cache.get_data = MagicMock(return_value=({}, {"cache_hit": False}))
    cache.get_binary_data = MagicMock(return_value=({}, {"cache_hit": False}))

    # Return HTML content for fetch
    client.fetch = MagicMock(
        return_value=(
            """
        <html>
        <body>
            <dl class="variablelist">
                <dt>
                    <a id="opt-system.defaults.dock.autohide"></a>
                    <code class="option">system.defaults.dock.autohide</code>
                </dt>
                <dd>
                    <p>Whether to automatically hide and show the dock.</p>
                    <p><span class="emphasis"><em>Type:</em></span> boolean</p>
                    <p><span class="emphasis"><em>Default:</em></span> false</p>
                </dd>
            </dl>
        </body>
        </html>
        """,
            {"success": True},
        )
    )

    return client


@pytest.mark.asyncio
async def test_save_to_filesystem_cache(mock_html_client):
    """Test saving data to filesystem cache."""
    # Create client with our mock
    client = DarwinClient(html_client=mock_html_client)

    # Populate data
    client.options = {
        "system.defaults.dock.autohide": DarwinOption(
            name="system.defaults.dock.autohide",
            description="Whether to automatically hide and show the dock.",
            type="boolean",
            default="false",
        )
    }
    client.name_index["system"] = ["system.defaults.dock.autohide"]
    client.name_index["system.defaults"] = ["system.defaults.dock.autohide"]
    client.name_index["system.defaults.dock"] = ["system.defaults.dock.autohide"]
    client.word_index["dock"].add("system.defaults.dock.autohide")
    client.word_index["hide"].add("system.defaults.dock.autohide")
    client.prefix_index["system"] = ["system.defaults.dock.autohide"]
    client.total_options = 1
    client.total_categories = 1
    client.last_updated = datetime.now()

    # Call the method
    result = await client._save_to_filesystem_cache()

    # Check results
    assert result is True

    # Verify cache.set_data was called with correct data
    set_data_call = mock_html_client.cache.set_data.call_args
    assert set_data_call is not None
    assert client.cache_key == set_data_call[0][0]
    data = set_data_call[0][1]
    assert "options" in data
    assert "total_options" in data
    assert data["total_options"] == 1
    assert "last_updated" in data

    # Verify options were serialized as dictionaries (not DarwinOption objects)
    assert isinstance(data["options"], dict)
    option_entry = list(data["options"].values())[0]
    assert isinstance(option_entry, dict)
    assert "name" in option_entry
    assert "description" in option_entry

    # Verify cache.set_binary_data was called with correct data
    set_binary_call = mock_html_client.cache.set_binary_data.call_args
    assert set_binary_call is not None
    assert client.cache_key == set_binary_call[0][0]
    binary_data = set_binary_call[0][1]
    assert "name_index" in binary_data
    assert "word_index" in binary_data
    assert "prefix_index" in binary_data
    # Check word_index structure (converted from sets to lists)
    assert isinstance(binary_data["word_index"]["dock"], list)


@pytest.mark.asyncio
async def test_load_from_filesystem_cache(mock_html_client):
    """Test loading data from filesystem cache."""
    # Create client with our mock
    client = DarwinClient(html_client=mock_html_client)

    # Setup test data is done directly in serialized_cache_data below

    cache_binary_data = {
        "name_index": {
            "system": ["system.defaults.dock.autohide"],
            "system.defaults": ["system.defaults.dock.autohide"],
            "system.defaults.dock": ["system.defaults.dock.autohide"],
        },
        "word_index": {"dock": ["system.defaults.dock.autohide"], "hide": ["system.defaults.dock.autohide"]},
        "prefix_index": {
            "system": ["system.defaults.dock.autohide"],
            "system.defaults": ["system.defaults.dock.autohide"],
            "system.defaults.dock": ["system.defaults.dock.autohide"],
        },
    }

    # Convert test option to dict format for JSON serialization
    option_dict = {
        "name": "system.defaults.dock.autohide",
        "description": "Whether to automatically hide and show the dock.",
        "type": "boolean",
        "default": "false",
        "example": "",
        "declared_by": "",
        "sub_options": [],
        "parent": None,
    }

    # Configure mocks to return cache hits with dictionary options
    serialized_cache_data = {
        "options": {"system.defaults.dock.autohide": option_dict},
        "total_options": 1,
        "total_categories": 1,
        "last_updated": datetime.now().isoformat(),
        "timestamp": 123456789.0,
    }

    mock_html_client.cache.get_data.return_value = (serialized_cache_data, {"cache_hit": True})
    mock_html_client.cache.get_binary_data.return_value = (cache_binary_data, {"cache_hit": True})

    # Call the method
    result = await client._load_from_filesystem_cache()

    # Check results
    assert result is True
    assert len(client.options) == 1
    assert "system.defaults.dock.autohide" in client.options
    assert client.total_options == 1
    assert client.total_categories == 1

    # Verify dictionary was converted back to DarwinOption object
    assert isinstance(client.options["system.defaults.dock.autohide"], DarwinOption)
    option = client.options["system.defaults.dock.autohide"]
    assert option.name == "system.defaults.dock.autohide"
    assert option.description == "Whether to automatically hide and show the dock."
    assert option.type == "boolean"
    assert option.default == "false"

    # Verify indices were loaded correctly
    assert "system" in client.name_index
    assert "system.defaults" in client.name_index
    assert "system.defaults.dock" in client.name_index

    # Verify word_index was converted back to sets
    assert "dock" in client.word_index
    assert isinstance(client.word_index["dock"], set)
    assert "system.defaults.dock.autohide" in client.word_index["dock"]


@pytest.mark.asyncio
async def test_load_options_from_cache(mock_html_client):
    """Test the full load_options method with cache."""
    # Create client with our mock
    client = DarwinClient(html_client=mock_html_client)

    # First test with cold cache (cache miss)
    result = await client.load_options()

    # Verify result has options
    assert len(result) > 0
    assert mock_html_client.fetch.called
    assert client.loading_status == "loaded"

    # Now test with a warm cache
    mock_html_client.reset_mock()

    # Setup cache hit for memory cache
    test_cache_data = {
        "options": {
            "system.defaults.dock.autohide": DarwinOption(
                name="system.defaults.dock.autohide", description="From cache", type="boolean"
            )
        },
        "name_index": {"system": ["system.defaults.dock.autohide"]},
        "word_index": {"dock": ["system.defaults.dock.autohide"]},
        "prefix_index": {"system": ["system.defaults.dock.autohide"]},
        "total_options": 1,
        "total_categories": 1,
        "last_updated": datetime.now(),
    }

    # Mock memory cache to return data
    with patch("nixmcp.cache.simple_cache.SimpleCache.get", return_value=test_cache_data):
        result = await client.load_options()

        # Verify we got our cached data
        assert "system.defaults.dock.autohide" in result
        assert result["system.defaults.dock.autohide"].description == "From cache"

        # Verify we didn't call fetch
        assert not mock_html_client.fetch.called


@pytest.mark.asyncio
async def test_invalidate_cache(mock_html_client):
    """Test cache invalidation."""
    # Create client with our mock
    with patch("nixmcp.cache.simple_cache.SimpleCache") as mock_simple_cache:
        # Set up the mock SimpleCache
        mock_cache_instance = MagicMock()
        mock_cache_instance.cache = {"darwin_data_v1.0.0": (time.time(), {"some": "data"})}
        mock_simple_cache.return_value = mock_cache_instance

        client = DarwinClient(html_client=mock_html_client)

        # Call invalidate
        client.invalidate_cache()

        # Verify filesystem cache invalidation calls
        mock_html_client.cache.invalidate_data.assert_called_once_with(client.cache_key)
        mock_html_client.cache.invalidate.assert_called_once_with(client.OPTION_REFERENCE_URL)
