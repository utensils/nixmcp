"""
Tests for NixOS-specific MCP completion implementations.

This module tests the NixOS-specific completion implementations for packages,
options, programs, and tool arguments.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nixmcp.completions.nixos import (
    complete_nixos_package_name,
    complete_nixos_option_name,
    complete_nixos_program_name,
    complete_nixos_search_arguments,
    complete_nixos_info_arguments,
)


@pytest.mark.asyncio
async def test_complete_nixos_package_name_empty():
    """Test NixOS package name completion with empty input."""
    # Mock Elasticsearch client
    es_client = MagicMock()

    # Test with empty package name
    result = await complete_nixos_package_name("", es_client)

    # Verify default suggestions are returned
    assert isinstance(result, dict)
    assert "items" in result
    assert len(result["items"]) > 0
    assert all(isinstance(item, dict) for item in result["items"])
    assert all("label" in item and "value" in item for item in result["items"])


@pytest.mark.asyncio
async def test_complete_nixos_package_name_with_input():
    """Test NixOS package name completion with input."""
    # Create mock Elasticsearch client with stubbed response
    es_client = MagicMock()
    es_client.safe_elasticsearch_query.return_value = {
        "hits": {"hits": [{"_source": {"package_attr_name": "firefox", "package_description": "A web browser"}}]}
    }

    # Test with package name
    result = await complete_nixos_package_name("firefox", es_client)

    # Verify Elasticsearch was queried and results are returned
    es_client.safe_elasticsearch_query.assert_called_once()
    assert isinstance(result, dict)
    assert "items" in result
    assert len(result["items"]) == 1
    assert result["items"][0]["label"] == "firefox"
    assert result["items"][0]["value"] == "firefox"


@pytest.mark.asyncio
async def test_complete_nixos_option_name_empty():
    """Test NixOS option name completion with empty input."""
    # Mock Elasticsearch client
    es_client = MagicMock()

    # Test with empty option name
    result = await complete_nixos_option_name("", es_client)

    # Verify default suggestions are returned
    assert isinstance(result, dict)
    assert "items" in result
    assert len(result["items"]) > 0
    assert all(isinstance(item, dict) for item in result["items"])
    assert all("label" in item and "value" in item for item in result["items"])


@pytest.mark.asyncio
async def test_complete_nixos_option_name_hierarchical():
    """Test NixOS option name completion with hierarchical path."""
    # Create mock Elasticsearch client with stubbed response
    es_client = MagicMock()
    es_client.safe_elasticsearch_query.return_value = {
        "hits": {
            "hits": [
                {
                    "_source": {
                        "option_name": "services.postgresql.enable",
                        "option_description": "Enable PostgreSQL server",
                        "option_type": "boolean",
                    }
                }
            ]
        }
    }

    # Test with hierarchical option path
    result = await complete_nixos_option_name("services.postgresql", es_client)

    # Verify Elasticsearch was queried and results are returned
    es_client.safe_elasticsearch_query.assert_called_once()
    assert isinstance(result, dict)
    assert "items" in result
    assert len(result["items"]) == 1
    assert result["items"][0]["label"] == "services.postgresql.enable"
    assert result["items"][0]["value"] == "services.postgresql.enable"


@pytest.mark.asyncio
async def test_complete_nixos_program_name_empty():
    """Test NixOS program name completion with empty input."""
    # Mock Elasticsearch client
    es_client = MagicMock()

    # Test with empty program name
    result = await complete_nixos_program_name("", es_client)

    # Verify default suggestions are returned
    assert isinstance(result, dict)
    assert "items" in result
    assert len(result["items"]) > 0
    assert all(isinstance(item, dict) for item in result["items"])
    assert all("label" in item and "value" in item for item in result["items"])


@pytest.mark.asyncio
async def test_complete_nixos_program_name_with_input():
    """Test NixOS program name completion with input."""
    # Create mock Elasticsearch client with stubbed response
    es_client = MagicMock()
    es_client.safe_elasticsearch_query.return_value = {
        "aggregations": {"unique_programs": {"buckets": [{"key": "python", "doc_count": 5}]}},
        "hits": {"hits": [{"_source": {"package_attr_name": "python3", "package_programs": ["python", "python3"]}}]},
    }

    # Test with program name
    result = await complete_nixos_program_name("python", es_client)

    # Verify Elasticsearch was queried and results are returned
    es_client.safe_elasticsearch_query.assert_called_once()
    assert isinstance(result, dict)
    assert "items" in result
    assert len(result["items"]) == 1
    assert result["items"][0]["label"] == "python"
    assert result["items"][0]["value"] == "python"


@pytest.mark.asyncio
async def test_complete_nixos_search_arguments_query():
    """Test NixOS search arguments completion for query parameter."""
    # Mock NixOS context
    nixos_context = MagicMock()
    es_client = MagicMock()
    nixos_context.get_es_client.return_value = es_client

    # Mock package name completion for query parameter
    with patch("nixmcp.completions.nixos.complete_nixos_package_name", new_callable=AsyncMock) as mock_package:
        mock_package.return_value = {"items": [{"label": "test", "value": "test"}]}

        # Test with query argument
        result = await complete_nixos_search_arguments("query", "test", nixos_context)

        # For non-empty query, package completion should be called
        mock_package.assert_called_once_with("test", es_client, is_search=True)
        assert result == {"items": [{"label": "test", "value": "test"}]}


@pytest.mark.asyncio
async def test_complete_nixos_search_arguments_type():
    """Test NixOS search arguments completion for type parameter."""
    # Mock NixOS context
    nixos_context = MagicMock()

    # Test with type argument
    result = await complete_nixos_search_arguments("type", "pack", nixos_context)

    # Verify type enum suggestions are filtered and returned
    assert isinstance(result, dict)
    assert "items" in result
    assert len(result["items"]) == 1
    assert result["items"][0]["label"] == "packages"
    assert result["items"][0]["value"] == "packages"


@pytest.mark.asyncio
async def test_complete_nixos_search_arguments_channel():
    """Test NixOS search arguments completion for channel parameter."""
    # Mock NixOS context
    nixos_context = MagicMock()

    # Test with channel argument
    result = await complete_nixos_search_arguments("channel", "unst", nixos_context)

    # Verify channel enum suggestions are filtered and returned
    assert isinstance(result, dict)
    assert "items" in result
    assert len(result["items"]) == 1
    assert result["items"][0]["label"] == "unstable"
    assert result["items"][0]["value"] == "unstable"


@pytest.mark.asyncio
async def test_complete_nixos_info_arguments_name():
    """Test NixOS info arguments completion for name parameter."""
    # Mock NixOS context
    nixos_context = MagicMock()
    es_client = MagicMock()
    nixos_context.get_es_client.return_value = es_client

    # Mock package name completion for name parameter
    with patch("nixmcp.completions.nixos.complete_nixos_package_name", new_callable=AsyncMock) as mock_package:
        mock_package.return_value = {"items": [{"label": "test", "value": "test"}]}

        # Test with name argument
        result = await complete_nixos_info_arguments("name", "test", nixos_context)

        # For non-empty name, package completion should be called
        mock_package.assert_called_once_with("test", es_client)
        assert result == {"items": [{"label": "test", "value": "test"}]}


@pytest.mark.asyncio
async def test_complete_nixos_info_arguments_type():
    """Test NixOS info arguments completion for type parameter."""
    # Mock NixOS context
    nixos_context = MagicMock()

    # Test with type argument
    result = await complete_nixos_info_arguments("type", "pack", nixos_context)

    # Verify type enum suggestions are filtered and returned
    assert isinstance(result, dict)
    assert "items" in result
    assert len(result["items"]) == 1
    assert result["items"][0]["label"] == "package"
    assert result["items"][0]["value"] == "package"
