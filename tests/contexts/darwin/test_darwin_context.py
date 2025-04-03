"""Tests for the Darwin context."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

# Mark all tests in this module as asyncio and integration tests
pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

from mcp_nixos.clients.darwin.darwin_client import DarwinClient
from mcp_nixos.contexts.darwin.darwin_context import DarwinContext


@pytest.fixture
def mock_darwin_client():
    """Create a mock Darwin client for testing."""
    client = MagicMock(spec=DarwinClient)
    client.load_options = AsyncMock(return_value={})
    client.search_options = AsyncMock(return_value=[])
    client.get_option = AsyncMock(return_value=None)
    client.get_options_by_prefix = AsyncMock(return_value=[])
    client.get_categories = AsyncMock(return_value=[])
    client.get_statistics = AsyncMock(
        return_value={
            "total_options": 0,
            "total_categories": 0,
            "last_updated": None,
            "loading_status": "not_loaded",
            "categories": [],
        }
    )
    return client


@pytest.fixture
def darwin_context(mock_darwin_client):
    """Create a Darwin context for testing."""
    return DarwinContext(darwin_client=mock_darwin_client)


@pytest.mark.asyncio
async def test_startup_success(darwin_context):
    """Test successful startup of Darwin context."""
    # Configure mock to return quickly
    darwin_context.client.load_options.return_value = {"test": "option"}
    darwin_context.client.total_options = 10

    # Call startup
    await darwin_context.startup()

    # Check that the client was called and status was updated
    darwin_context.client.load_options.assert_called_once_with(force_refresh=False)
    assert darwin_context.status == "loaded"


@pytest.mark.asyncio
async def test_startup_timeout(darwin_context):
    """Test startup with timeout."""

    # Configure mock to delay
    async def slow_load(*args, **kwargs):
        await asyncio.sleep(0.1)
        return {"test": "option"}

    darwin_context.client.load_options = AsyncMock(side_effect=slow_load)
    darwin_context.eager_loading_timeout = 0.05  # Set a very short timeout

    # Call startup
    await darwin_context.startup()

    # Check that background loading was triggered
    assert darwin_context.status == "loading_background"
    assert darwin_context.loading_task is not None


@pytest.mark.asyncio
async def test_startup_error(darwin_context):
    """Test startup with error."""
    # Configure mock to raise an exception
    darwin_context.client.load_options = AsyncMock(side_effect=ValueError("Test error"))

    # Call startup
    await darwin_context.startup()

    # Check that error was handled
    assert darwin_context.status == "error"
    assert darwin_context.error is not None
    assert darwin_context.loading_task is not None


@pytest.mark.asyncio
async def test_shutdown(darwin_context):
    """Test shutdown of Darwin context."""
    # Create a mock task
    task = MagicMock()
    task.done = MagicMock(return_value=False)
    task.cancel = MagicMock()
    darwin_context.loading_task = task

    # Call shutdown
    await darwin_context.shutdown()

    # Check that task was cancelled
    task.cancel.assert_called_once()
    assert darwin_context.status == "shutdown"


@pytest.mark.asyncio
async def test_get_status(darwin_context):
    """Test getting status from Darwin context."""
    # Set up test state
    darwin_context.status = "loaded"
    darwin_context.error = None
    darwin_context.client.get_statistics.return_value = {
        "total_options": 100,
        "total_categories": 10,
        "last_updated": "2025-03-26T12:00:00",
        "loading_status": "loaded",
        "categories": [],
    }

    # Call get_status
    stats = await darwin_context.get_status()

    # Check the result
    assert stats["status"] == "loaded"
    assert stats["error"] is None
    assert stats["options_count"] == 100
    assert stats["categories_count"] == 10
    assert stats["last_updated"] == "2025-03-26T12:00:00"


@pytest.mark.asyncio
async def test_search_options(darwin_context):
    """Test searching options through Darwin context."""
    # Set up test data
    darwin_context.status = "loaded"
    darwin_context.client.search_options.return_value = [{"name": "test.option", "description": "Test option"}]

    # Call search_options
    results = await darwin_context.search_options("test")

    # Check the result
    assert len(results) == 1
    assert results[0]["name"] == "test.option"
    darwin_context.client.search_options.assert_called_once_with("test", limit=20)


@pytest.mark.asyncio
async def test_get_option(darwin_context):
    """Test getting a specific option through Darwin context."""
    # Set up test data
    darwin_context.status = "loaded"
    darwin_context.client.get_option.return_value = {
        "name": "test.option",
        "description": "Test option",
        "type": "boolean",
        "default": "false",
    }

    # Call get_option
    option = await darwin_context.get_option("test.option")

    # Check the result
    assert option is not None
    assert option["name"] == "test.option"
    assert option["type"] == "boolean"
    darwin_context.client.get_option.assert_called_once_with("test.option")


@pytest.mark.asyncio
async def test_get_options_by_prefix(darwin_context):
    """Test getting options by prefix through Darwin context."""
    # Set up test data
    darwin_context.status = "loaded"
    darwin_context.client.get_options_by_prefix.return_value = [
        {"name": "test.prefix.option1", "description": "Test option 1"},
        {"name": "test.prefix.option2", "description": "Test option 2"},
    ]

    # Call get_options_by_prefix
    options = await darwin_context.get_options_by_prefix("test.prefix")

    # Check the result
    assert len(options) == 2
    assert options[0]["name"] == "test.prefix.option1"
    assert options[1]["name"] == "test.prefix.option2"
    darwin_context.client.get_options_by_prefix.assert_called_once_with("test.prefix")


@pytest.mark.asyncio
async def test_get_categories(darwin_context):
    """Test getting categories through Darwin context."""
    # Set up test data
    darwin_context.status = "loaded"
    darwin_context.client.get_categories.return_value = [
        {"name": "system", "option_count": 10, "path": "system"},
        {"name": "services", "option_count": 15, "path": "services"},
    ]

    # Call get_categories
    categories = await darwin_context.get_categories()

    # Check the result
    assert len(categories) == 2
    assert categories[0]["name"] == "system"
    assert categories[1]["name"] == "services"
    darwin_context.client.get_categories.assert_called_once()


@pytest.mark.asyncio
async def test_get_statistics(darwin_context):
    """Test getting statistics through Darwin context."""
    # Set up test data
    darwin_context.status = "loaded"
    darwin_context.client.get_statistics.return_value = {
        "total_options": 100,
        "total_categories": 10,
        "last_updated": "2025-03-26T12:00:00",
        "loading_status": "loaded",
        "categories": [
            {"name": "system", "option_count": 10, "path": "system"},
            {"name": "services", "option_count": 15, "path": "services"},
        ],
    }

    # Call get_statistics
    stats = await darwin_context.get_statistics()

    # Check the result
    assert stats["total_options"] == 100
    assert stats["total_categories"] == 10
    assert stats["last_updated"] == "2025-03-26T12:00:00"
    assert len(stats["categories"]) == 2
    darwin_context.client.get_statistics.assert_called_once()
