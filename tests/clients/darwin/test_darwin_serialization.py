"""Test Darwin client serialization in cache."""

import os
import shutil
import tempfile
import pytest

# Mark as integration test by default
pytestmark = pytest.mark.integration

from mcp_nixos.clients.darwin.darwin_client import DarwinClient


@pytest.fixture
def temp_cache_dir():
    """Create a temporary directory for cache testing."""
    temp_dir = tempfile.mkdtemp(prefix="mcp_nixos_test_cache_")
    old_cache_dir = os.environ.get("MCP_NIXOS_CACHE_DIR")

    # Set environment variable to use our temp dir
    os.environ["MCP_NIXOS_CACHE_DIR"] = temp_dir

    yield temp_dir

    # Cleanup
    if old_cache_dir:
        os.environ["MCP_NIXOS_CACHE_DIR"] = old_cache_dir
    else:
        del os.environ["MCP_NIXOS_CACHE_DIR"]

    shutil.rmtree(temp_dir)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_darwin_cache_serialization_integration(temp_cache_dir):
    """Test Darwin client's cache serialization with real filesystem integration."""
    # Create a Darwin client with a real filesystem cache
    client = DarwinClient()

    # Mock the fetch_url method to return a simple HTML snippet
    html_content = """
    <html>
    <body>
        <dl>
            <dt>
                <a id="opt-test.option1"></a>
                <code>test.option1</code>
            </dt>
            <dd>
                Test option 1 description.
                *Type:* string
                *Default:* default value 1
            </dd>
            <dt>
                <a id="opt-test.option2"></a>
                <code>test.option2</code>
            </dt>
            <dd>
                Test option 2 description.
                *Type:* int
                *Default:* default value 2
            </dd>
            <dt>
                <a id="opt-test.option3"></a>
                <code>test.option3</code>
            </dt>
            <dd>
                Test option 3 description.
                *Type:* boolean
                *Default:* default value 3
            </dd>
            <dt>
                <a id="opt-test.option4"></a>
                <code>test.option4</code>
            </dt>
            <dd>
                Test option 4 description.
                *Type:* string
                *Default:* default value 4
            </dd>
            <dt>
                <a id="opt-test.option5"></a>
                <code>test.option5</code>
            </dt>
            <dd>
                Test option 5 description.
                *Type:* string
                *Default:* default value 5
            </dd>
            <dt>
                <a id="opt-test.option6"></a>
                <code>test.option6</code>
            </dt>
            <dd>
                Test option 6 description.
                *Type:* string
                *Default:* default value 6
            </dd>
            <dt>
                <a id="opt-test.option7"></a>
                <code>test.option7</code>
            </dt>
            <dd>
                Test option 7 description.
                *Type:* string
                *Default:* default value 7
            </dd>
            <dt>
                <a id="opt-test.option8"></a>
                <code>test.option8</code>
            </dt>
            <dd>
                Test option 8 description.
                *Type:* string
                *Default:* default value 8
            </dd>
            <dt>
                <a id="opt-test.option9"></a>
                <code>test.option9</code>
            </dt>
            <dd>
                Test option 9 description.
                *Type:* string
                *Default:* default value 9
            </dd>
            <dt>
                <a id="opt-test.option10"></a>
                <code>test.option10</code>
            </dt>
            <dd>
                Test option 10 description.
                *Type:* string
                *Default:* default value 10
            </dd>
        </dl>
    </body>
    </html>
    """

    async def mock_fetch_url(*args, **kwargs):
        return html_content

    client.fetch_url = mock_fetch_url

    # Load options (this will parse the mock HTML and create the cache)
    await client.load_options()

    # Verify we have the parsed options
    assert len(client.options) >= 10, f"Expected at least 10 options, got {len(client.options)}"
    assert "test.option1" in client.options

    # Create a new client that should load from cache
    new_client = DarwinClient()

    # Create a mock that we can track was not called
    fetch_url_called = False

    async def mock_fetch_url_should_not_be_called(*args, **kwargs):
        nonlocal fetch_url_called
        fetch_url_called = True
        return "This should not be returned because cache should be used"

    new_client.fetch_url = mock_fetch_url_should_not_be_called

    # Load options (should load from cache, not call fetch_url)
    await new_client.load_options()

    # Verify data was loaded correctly from cache
    assert (
        len(new_client.options) >= 10
    ), f"Expected at least 10 options loaded from cache, got {len(new_client.options)}"
    assert "test.option1" in new_client.options

    # The parser may combine all text content into the description, so just check that the core info is there
    assert "Test option 1 description" in new_client.options["test.option1"].description
    # Just make sure some basic properties are included
    assert "string" in new_client.options["test.option1"].type
    assert "default value 1" in new_client.options["test.option1"].default

    # Verify fetch_url wasn't called
    assert not fetch_url_called, "fetch_url should not have been called because data should load from cache"
