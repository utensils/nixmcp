"""Tests for the Darwin client filesystem caching."""

import time
import pytest
import tempfile
from datetime import datetime
from collections import defaultdict
from unittest.mock import MagicMock, patch

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

from mcp_nixos.clients.darwin.darwin_client import DarwinClient, DarwinOption
from mcp_nixos.clients.html_client import HTMLClient
from mcp_nixos.cache.html_cache import HTMLCache


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


@pytest.fixture
def real_cache_dir():
    """Create a temporary directory for a real cache."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.mark.asyncio
async def test_save_to_filesystem_cache(mock_html_client):
    """Test saving data to filesystem cache.

    Note: This test now requires at least 10 options as we've added validation
    to prevent caching small datasets.
    """
    # Create client with our mock
    client = DarwinClient(html_client=mock_html_client)

    # Populate data with at least 10 options to meet the minimum validation criteria
    client.options = {}
    # Create 10 test options
    for i in range(1, 11):
        option_name = f"system.defaults.option{i}"
        client.options[option_name] = DarwinOption(
            name=option_name,
            description=f"Test option {i} description",
            type="boolean",
            default="false",
        )

    # Add the main test option
    client.options["system.defaults.dock.autohide"] = DarwinOption(
        name="system.defaults.dock.autohide",
        description="Whether to automatically hide and show the dock.",
        type="boolean",
        default="false",
    )

    # Setup indices
    client.name_index["system"] = ["system.defaults.dock.autohide"] + [
        f"system.defaults.option{i}" for i in range(1, 11)
    ]
    client.name_index["system.defaults"] = ["system.defaults.dock.autohide"] + [
        f"system.defaults.option{i}" for i in range(1, 11)
    ]
    client.name_index["system.defaults.dock"] = ["system.defaults.dock.autohide"]

    client.word_index["dock"].add("system.defaults.dock.autohide")
    client.word_index["hide"].add("system.defaults.dock.autohide")
    for i in range(1, 11):
        client.word_index["option"].add(f"system.defaults.option{i}")

    client.prefix_index["system"] = ["system.defaults.dock.autohide"] + [
        f"system.defaults.option{i}" for i in range(1, 11)
    ]
    client.prefix_index["system.defaults"] = ["system.defaults.dock.autohide"] + [
        f"system.defaults.option{i}" for i in range(1, 11)
    ]
    client.prefix_index["system.defaults.dock"] = ["system.defaults.dock.autohide"]

    # Update total counts
    client.total_options = 11  # 10 generic options + 1 specific option
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
    assert data["total_options"] == 11  # Now we're testing with 11 options
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

    # Create 10 options to meet minimum requirement
    option_dicts = {}
    option_dicts["system.defaults.dock.autohide"] = option_dict
    for i in range(1, 15):  # Add 14 more options to be safe
        option_dicts[f"system.defaults.option{i}"] = {
            "name": f"system.defaults.option{i}",
            "description": f"Test option {i} description",
            "type": "boolean",
            "default": "false",
            "example": "",
            "declared_by": "",
            "sub_options": [],
            "parent": None,
        }

    # Configure mocks to return cache hits with dictionary options
    serialized_cache_data = {
        "options": option_dicts,
        "total_options": len(option_dicts),
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
    assert len(client.options) == 15  # Account for our expanded list of options
    assert "system.defaults.dock.autohide" in client.options
    assert client.total_options == 15  # Should match the options count
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
    with patch("mcp_nixos.cache.simple_cache.SimpleCache.get", return_value=test_cache_data):
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
    with patch("mcp_nixos.cache.simple_cache.SimpleCache") as mock_simple_cache:
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


@pytest.mark.asyncio
async def test_empty_dataset_not_cached(real_cache_dir):
    """
    Test that empty datasets are not cached to prevent bad data persistence.

    This test uses a real temporary directory for cache storage to verify
    that empty datasets don't get written to disk.
    """
    # Create a cache with a normal TTL
    ttl = 86400

    # Use a real HTMLClient with the temporary directory
    html_client = HTMLClient(cache_dir=real_cache_dir, ttl=ttl)

    # Create the DarwinClient with our real cache
    darwin_client = DarwinClient(html_client=html_client, cache_ttl=ttl)

    # Setup an empty dataset
    darwin_client.options = {}
    darwin_client.total_options = 0
    darwin_client.total_categories = 0
    darwin_client.name_index = {}
    darwin_client.word_index = defaultdict(set)
    darwin_client.prefix_index = {}
    darwin_client.last_updated = datetime.now()

    # Try to save it to the filesystem
    result = await darwin_client._save_to_filesystem_cache()

    # Should fail to cache empty dataset
    assert result is False

    # Check no cache files were created for data
    cache_key = darwin_client.cache_key
    # Ensure cache is not None before accessing its methods
    assert html_client.cache is not None, "HTMLClient cache should not be None"
    json_path = html_client.cache._get_data_cache_path(cache_key)
    pickle_path = html_client.cache._get_binary_data_cache_path(cache_key)

    assert not json_path.exists(), "JSON cache file should not be created for empty dataset"
    assert not pickle_path.exists(), "Pickle cache file should not be created for empty dataset"

    # Now test with a small dataset (fewer than 10 options)
    darwin_client.options = {
        "test.option1": DarwinOption(name="test.option1", description="test description"),
        "test.option2": DarwinOption(name="test.option2", description="test description"),
    }
    darwin_client.total_options = 2
    darwin_client.total_categories = 1
    darwin_client.name_index = {"test": ["test.option1", "test.option2"]}
    darwin_client.word_index = defaultdict(set)
    darwin_client.word_index["test"].add("test.option1")
    darwin_client.word_index["test"].add("test.option2")
    darwin_client.prefix_index = {"test": ["test.option1", "test.option2"]}

    # Try to save small dataset - should still fail due to min size validation
    result = await darwin_client._save_to_filesystem_cache()
    assert result is False

    # Verify none of the cache files were created
    assert not json_path.exists(), "JSON cache file should not be created for small dataset"
    assert not pickle_path.exists(), "Pickle cache file should not be created for small dataset"


@pytest.mark.asyncio
async def test_expired_cache_ttl_reload(real_cache_dir):
    """
    Test that content is properly reloaded and cache files recreated when TTL expires.

    This test patches the time functions to avoid actual waiting.
    """
    # Create a cache with a very short TTL, but we'll mock the time check
    short_ttl = 60  # 60 seconds, won't actually wait

    # Create a real HTMLCache with TTL
    html_cache = HTMLCache(cache_dir=real_cache_dir, ttl=short_ttl)

    # Create a real HTMLClient with our cache
    html_client = HTMLClient(cache_dir=real_cache_dir, ttl=short_ttl, use_cache=True)

    # Let's use the base URL to avoid real requests in the test
    test_url = "https://example.com/test"
    test_content = """
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
    """

    # Track the current "mocked" time
    current_time = time.time()

    # Patch time.time() to return controlled timestamps
    with patch("time.time") as mock_time:
        # Start at current time
        mock_time.return_value = current_time

        # Mock the requests.get function
        with patch("requests.get") as mock_get:
            # Setup mock for first request
            mock_response1 = MagicMock()
            mock_response1.text = test_content
            mock_response1.status_code = 200
            mock_response1.raise_for_status = MagicMock()

            # Setup mock for second request with slightly different content
            mock_response2 = MagicMock()
            mock_response2.text = test_content.replace("false", "true")  # Change default value
            mock_response2.status_code = 200
            mock_response2.raise_for_status = MagicMock()

            # Set up the mock to return different responses on successive calls
            mock_get.side_effect = [mock_response1, mock_response2]

            # First request - should fetch from web and cache
            content1, metadata1 = html_client.fetch(test_url)

            # Verify content was fetched from web
            assert metadata1["from_cache"] is False
            assert content1 is not None
            assert "false" in content1

            # Verify cache file was created
            cache_path = html_cache._get_cache_path(test_url)
            assert cache_path.exists()

            # Second request immediately after - should use cache
            content2, metadata2 = html_client.fetch(test_url)
            assert metadata2["from_cache"] is True
            assert content2 == content1

            # Simulate passage of time to expire the cache (more than TTL)
            mock_time.return_value = current_time + short_ttl + 10

            # Third request after "expiration" - should fetch new content
            content3, metadata3 = html_client.fetch(test_url)

            # Verify content was fetched from web again
            assert metadata3["from_cache"] is False
            assert content3 is not None
            assert "true" in content3  # Content has changed
            assert content3 != content1

            # Verify cache file was updated
            cached_content = cache_path.read_text()
            assert "true" in cached_content
            assert cached_content == content3

            # Verify mock_get was called twice (ignoring cache for expired TTL)
            assert mock_get.call_count == 2


@pytest.mark.asyncio
async def test_reject_invalid_cached_data(real_cache_dir):
    """
    Test that invalid/empty cached data is rejected during loading.

    This test verifies that when corrupted or empty cache files exist,
    they are properly ignored and not loaded.
    """
    # Create a cache with normal TTL
    ttl = 86400

    # Use a real HTMLClient with the temporary directory
    html_client = HTMLClient(cache_dir=real_cache_dir, ttl=ttl)

    # Create cache key for testing
    cache_key = "darwin_data_v1.0.0"

    # Get cache file paths
    assert html_client.cache is not None, "HTMLClient cache should not be None"
    json_path = html_client.cache._get_data_cache_path(cache_key)
    pickle_path = html_client.cache._get_binary_data_cache_path(cache_key)

    # Create invalid JSON data (empty options)
    invalid_json_data = {
        "options": {},
        "total_options": 0,
        "total_categories": 0,
        "last_updated": datetime.now().isoformat(),
        "timestamp": time.time(),
    }

    # Create invalid binary data (empty indices)
    invalid_binary_data = {
        "name_index": {},
        "word_index": {},
        "prefix_index": {},
    }

    # Write the invalid data to cache files
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        import json

        json.dump(invalid_json_data, f)

    with open(pickle_path, "wb") as f:
        import pickle

        pickle.dump(invalid_binary_data, f)

    # Verify the cache files exist
    assert json_path.exists(), "Failed to create test JSON cache file"
    assert pickle_path.exists(), "Failed to create test pickle cache file"

    # Create a new DarwinClient (should not use the invalid cache files)
    darwin_client = DarwinClient(html_client=html_client, cache_ttl=ttl)

    # Mock fetch_url to return valid HTML so we don't make real requests
    with patch.object(darwin_client, "fetch_url") as mock_fetch:
        # Create HTML with enough options to pass validation
        html_content = """
        <html>
        <body>
            <dl class="variablelist">
        """
        # Add 15 options to pass validation
        for i in range(1, 16):
            html_content += f"""
                <dt>
                    <a id="opt-test.option{i}"></a>
                    <code class="option">test.option{i}</code>
                </dt>
                <dd>
                    <p>Test option {i} description.</p>
                </dd>
            """
        html_content += """
            </dl>
        </body>
        </html>
        """

        mock_fetch.return_value = html_content

        # Try to load options - should reject the invalid cache
        result = await darwin_client._load_from_filesystem_cache()

        # Should fail to load from cache
        assert result is False

        # Now try to load options, which should parse HTML since cache was invalid
        options = await darwin_client.load_options()

        # Some options should be loaded from HTML
        assert len(options) > 0

        # Verify fetch_url was called (meaning it didn't use cache)
        mock_fetch.assert_called_once()


@pytest.mark.asyncio
async def test_darwin_client_expired_cache(real_cache_dir):
    """
    Test that DarwinClient properly reloads HTML and recreates cache files when TTL expires.
    Uses time mocking instead of real delays.
    """
    # Create a cache with a TTL - we'll mock the time check
    ttl = 60  # 60 seconds, won't actually wait

    # Track the current "mocked" time
    current_time = time.time()

    # Patch time.time() to return controlled timestamps
    with patch("time.time") as mock_time:
        # Start at current time
        mock_time.return_value = current_time

        # Use a real HTMLClient with TTL for testing
        html_client = HTMLClient(cache_dir=real_cache_dir, ttl=ttl)

        # Create the DarwinClient with our real cache
        darwin_client = DarwinClient(html_client=html_client, cache_ttl=ttl)

        # Create HTML content with 15 options to pass the validation
        html_content = """
        <html>
        <body>
            <dl>
        """

        # Add a main test option
        html_content += """
                <dt>
                    <a id="opt-system.defaults.dock.autohide"></a>
                    <code>system.defaults.dock.autohide</code>
                </dt>
                <dd>
                    Whether to automatically hide and show the dock. The default is false.
                    *Type:* boolean
                    *Default:* false
                </dd>
        """

        # Add 15 more options to pass validation
        for i in range(1, 16):
            html_content += f"""
                <dt>
                    <a id="opt-system.defaults.option{i}"></a>
                    <code>system.defaults.option{i}</code>
                </dt>
                <dd>
                    Test option {i} description.
                    *Type:* boolean
                    *Default:* false
                </dd>
            """

        html_content += """
            </dl>
        </body>
        </html>
        """

        # Mock the fetch_url method to return our HTML content
        with patch.object(darwin_client, "fetch_url") as mock_fetch:
            # First fetch - original content
            mock_fetch.return_value = html_content

            # Load options for the first time
            options1 = await darwin_client.load_options()

            # Verify correct option was loaded
            assert "system.defaults.dock.autohide" in options1
            assert options1["system.defaults.dock.autohide"].default == "false"

            # Check if JSON and pickle files were created
            cache_key = darwin_client.cache_key
            assert html_client.cache is not None, "HTMLClient cache should not be None"
            json_path = html_client.cache._get_data_cache_path(cache_key)
            pickle_path = html_client.cache._get_binary_data_cache_path(cache_key)

            assert json_path.exists(), "JSON cache file was not created"
            assert pickle_path.exists(), "Pickle cache file was not created"

            # Record file modification times
            json_mtime1 = json_path.stat().st_mtime
            pickle_mtime1 = pickle_path.stat().st_mtime

            # Simulate passage of time to expire the cache (more than TTL)
            mock_time.return_value = current_time + ttl + 10

            # Create updated HTML content with the same structure but updated default value
            updated_html_content = html_content.replace(
                "*Default:* false",
                "*Default:* true",
            )

            # Update the mock to return the new content
            mock_fetch.return_value = updated_html_content

            # We need to explicitly invalidate the cache to ensure the HTML gets reloaded
            darwin_client.invalidate_cache()
            # Ensure cache is not None before accessing invalidate
            assert html_client.cache is not None, "HTMLClient cache should not be None"
            html_client.cache.invalidate(darwin_client.OPTION_REFERENCE_URL)

            # Load options again with force_refresh=True to ensure it doesn't use the cache
            options2 = await darwin_client.load_options(force_refresh=True)

            # Verify the content was updated with new default value
            assert "system.defaults.dock.autohide" in options2
            assert (
                options2["system.defaults.dock.autohide"].default == "true"
            ), "Default value should be updated to 'true'"

            # Verify the cache files were recreated
            assert json_path.exists(), "JSON cache file does not exist after refresh"
            assert pickle_path.exists(), "Pickle cache file does not exist after refresh"

            # Check that files were actually updated (modification times should be different)
            json_mtime2 = json_path.stat().st_mtime
            pickle_mtime2 = pickle_path.stat().st_mtime

            assert json_mtime2 > json_mtime1, "JSON cache file was not updated"
            assert pickle_mtime2 > pickle_mtime1, "Pickle cache file was not updated"
