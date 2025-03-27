"""Tests for the Darwin client."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from bs4 import BeautifulSoup

from nixmcp.clients.darwin.darwin_client import DarwinClient, DarwinOption
from nixmcp.clients.html_client import HTMLClient
from nixmcp.cache.html_cache import HTMLCache
from nixmcp.cache.simple_cache import SimpleCache


@pytest.fixture
def sample_html():
    """Return sample HTML for testing."""
    return """
    <html>
    <body>
        <dl class="variablelist">
            <dt>
                <span class="term">
                    <a id="opt-system.defaults.dock.autohide"></a>
                    <a class="term" href="#opt-system.defaults.dock.autohide">
                        <code class="option">system.defaults.dock.autohide</code>
                    </a>
                </span>
            </dt>
            <dd>
                <p>Whether to automatically hide and show the dock.</p>
                <p><span class="emphasis"><em>Type:</em></span> boolean</p>
                <p><span class="emphasis"><em>Default:</em></span> false</p>
                <p><span class="emphasis"><em>Example:</em></span> true</p>
                <p>Declared by: <code>system/defaults.nix</code></p>
            </dd>
            <dt>
                <span class="term">
                    <a id="opt-system.defaults.dock.orientation"></a>
                    <a class="term" href="#opt-system.defaults.dock.orientation">
                        <code class="option">system.defaults.dock.orientation</code>
                    </a>
                </span>
            </dt>
            <dd>
                <p>Position of the dock on screen.</p>
                <div class="itemizedlist">Type: string</div>
                <div class="itemizedlist">Default: bottom</div>
                <div class="itemizedlist">Example: left</div>
                <div class="itemizedlist">Declared by: system/defaults.nix</div>
            </dd>
        </dl>
    </body>
    </html>
    """


@pytest.fixture
def mock_html_client(sample_html):
    """Create a mock HTML client."""
    client = MagicMock(spec=HTMLClient)
    client.fetch = MagicMock(return_value=(sample_html, {"success": True}))
    return client


@pytest.fixture
def mock_html_cache():
    """Create a mock HTML cache."""
    cache = MagicMock(spec=HTMLCache)
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=None)
    return cache


@pytest.fixture
def mock_memory_cache():
    """Create a mock memory cache."""
    cache = MagicMock(spec=SimpleCache)
    # SimpleCache methods are synchronous, not async
    cache.get = MagicMock(return_value=None)
    cache.set = MagicMock(return_value=None)
    return cache


@pytest.fixture
def darwin_client(mock_html_client, mock_html_cache, mock_memory_cache):
    """Create a Darwin client for testing."""
    with (
        patch("nixmcp.clients.darwin.darwin_client.HTMLCache", return_value=mock_html_cache),
        patch("nixmcp.clients.darwin.darwin_client.SimpleCache", return_value=mock_memory_cache),
    ):
        client = DarwinClient(html_client=mock_html_client)
        return client


@pytest.mark.asyncio
async def test_load_options(darwin_client, sample_html):
    """Test loading options from HTML."""
    # Mock the memory cache to return None to force HTML parsing
    darwin_client.memory_cache.get = MagicMock(return_value=None)

    # Call the method
    result = await darwin_client.load_options()

    # Check that options were loaded
    assert "system.defaults.dock.autohide" in result
    assert "system.defaults.dock.orientation" in result
    assert darwin_client.total_options == 2
    assert darwin_client.total_categories == 1
    assert darwin_client.loading_status == "loaded"


@pytest.mark.asyncio
async def test_parse_options(darwin_client, sample_html):
    """Test parsing options from HTML."""
    soup = BeautifulSoup(sample_html, "html.parser")
    await darwin_client._parse_options(soup)

    # Check that options were parsed correctly
    assert "system.defaults.dock.autohide" in darwin_client.options
    assert "system.defaults.dock.orientation" in darwin_client.options

    # Check option details
    option = darwin_client.options["system.defaults.dock.autohide"]
    assert option.name == "system.defaults.dock.autohide"
    assert "hide and show the dock" in option.description
    assert "boolean" in option.type
    assert "false" in option.default
    assert "true" in option.example

    # Check indices
    assert "system" in darwin_client.name_index
    assert "system.defaults" in darwin_client.name_index
    assert "system.defaults.dock" in darwin_client.name_index
    assert "system.defaults.dock.autohide" in darwin_client.name_index

    # Check word index
    assert "hide" in darwin_client.word_index
    assert "dock" in darwin_client.word_index
    assert len(darwin_client.word_index["dock"]) > 0


@pytest.mark.asyncio
async def test_search_options(darwin_client):
    """Test searching for options."""
    # Set up test data
    darwin_client.options = {
        "system.defaults.dock.autohide": DarwinOption(
            name="system.defaults.dock.autohide",
            description="Whether to automatically hide and show the dock.",
            type="boolean",
            default="false",
            example="true",
            declared_by="system/defaults.nix",
        ),
        "system.defaults.dock.orientation": DarwinOption(
            name="system.defaults.dock.orientation",
            description="Position of the dock on screen.",
            type="string",
            default="bottom",
            example="left",
            declared_by="system/defaults.nix",
        ),
    }
    darwin_client.name_index = {
        "system": ["system.defaults.dock.autohide", "system.defaults.dock.orientation"],
        "system.defaults": ["system.defaults.dock.autohide", "system.defaults.dock.orientation"],
        "system.defaults.dock": ["system.defaults.dock.autohide", "system.defaults.dock.orientation"],
        "system.defaults.dock.autohide": ["system.defaults.dock.autohide"],
        "system.defaults.dock.orientation": ["system.defaults.dock.orientation"],
    }
    darwin_client.word_index = {
        "dock": {"system.defaults.dock.autohide", "system.defaults.dock.orientation"},
        "hide": {"system.defaults.dock.autohide"},
        "orientation": {"system.defaults.dock.orientation"},
    }
    darwin_client.prefix_index = {
        "system": ["system.defaults.dock.autohide", "system.defaults.dock.orientation"],
        "system.defaults": ["system.defaults.dock.autohide", "system.defaults.dock.orientation"],
        "system.defaults.dock": ["system.defaults.dock.autohide", "system.defaults.dock.orientation"],
    }

    # Test exact match
    results = await darwin_client.search_options("system.defaults.dock.autohide")
    assert len(results) >= 1  # It may match both due to how search works
    assert any(r["name"] == "system.defaults.dock.autohide" for r in results)

    # Test prefix match
    results = await darwin_client.search_options("system.defaults.dock")
    assert len(results) == 2
    names = [r["name"] for r in results]
    assert "system.defaults.dock.autohide" in names
    assert "system.defaults.dock.orientation" in names

    # Test word match
    results = await darwin_client.search_options("hide")
    assert len(results) == 1
    assert results[0]["name"] == "system.defaults.dock.autohide"


@pytest.mark.asyncio
async def test_get_option(darwin_client):
    """Test getting a specific option."""
    # Set up test data
    darwin_client.options = {
        "system.defaults.dock.autohide": DarwinOption(
            name="system.defaults.dock.autohide",
            description="Whether to automatically hide and show the dock.",
            type="boolean",
            default="false",
            example="true",
            declared_by="system/defaults.nix",
        )
    }

    # Test getting an existing option
    option = await darwin_client.get_option("system.defaults.dock.autohide")
    assert option is not None
    assert option["name"] == "system.defaults.dock.autohide"
    assert "hide and show the dock" in option["description"]
    assert option["type"] == "boolean"

    # Test getting a non-existent option
    option = await darwin_client.get_option("nonexistent")
    assert option is None


@pytest.mark.asyncio
async def test_get_options_by_prefix(darwin_client):
    """Test getting options by prefix."""
    # Set up test data
    darwin_client.options = {
        "system.defaults.dock.autohide": DarwinOption(
            name="system.defaults.dock.autohide",
            description="Whether to automatically hide and show the dock.",
            type="boolean",
            default="false",
            example="true",
            declared_by="system/defaults.nix",
        ),
        "system.defaults.dock.orientation": DarwinOption(
            name="system.defaults.dock.orientation",
            description="Position of the dock on screen.",
            type="string",
            default="bottom",
            example="left",
            declared_by="system/defaults.nix",
        ),
        "system.keyboard.enableKeyMapping": DarwinOption(
            name="system.keyboard.enableKeyMapping",
            description="Whether to enable keyboard mapping.",
            type="boolean",
            default="false",
            example="true",
            declared_by="system/keyboard.nix",
        ),
    }
    darwin_client.prefix_index = {
        "system": [
            "system.defaults.dock.autohide",
            "system.defaults.dock.orientation",
            "system.keyboard.enableKeyMapping",
        ],
        "system.defaults": ["system.defaults.dock.autohide", "system.defaults.dock.orientation"],
        "system.defaults.dock": ["system.defaults.dock.autohide", "system.defaults.dock.orientation"],
        "system.keyboard": ["system.keyboard.enableKeyMapping"],
    }

    # Test getting options by prefix
    options = await darwin_client.get_options_by_prefix("system.defaults.dock")
    assert len(options) == 2
    names = [o["name"] for o in options]
    assert "system.defaults.dock.autohide" in names
    assert "system.defaults.dock.orientation" in names

    # Test getting options by a different prefix
    options = await darwin_client.get_options_by_prefix("system.keyboard")
    assert len(options) == 1
    assert options[0]["name"] == "system.keyboard.enableKeyMapping"


@pytest.mark.asyncio
async def test_fetch_url(darwin_client, sample_html):
    """Test the fetch_url adapter method."""
    # Setup the mock to return proper data
    darwin_client.html_client.fetch.return_value = (sample_html, {"success": True})

    # Test successful fetch
    result = await darwin_client.fetch_url("https://example.com")
    assert result == sample_html
    darwin_client.html_client.fetch.assert_called_once_with("https://example.com", force_refresh=False)

    # Test error handling
    darwin_client.html_client.fetch.reset_mock()
    darwin_client.html_client.fetch.return_value = (None, {"error": "Connection error"})

    with pytest.raises(ValueError) as excinfo:
        await darwin_client.fetch_url("https://example.com")

    assert "Connection error" in str(excinfo.value)
