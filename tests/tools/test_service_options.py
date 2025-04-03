# tests/tools/test_service_options.py

"""Tests for service path option handling and discovery in MCP-NixOS."""

import json

# Disable logging during tests
import logging
import unittest
import pytest
from unittest.mock import MagicMock, patch

# Mark as unit tests by default
pytestmark = pytest.mark.unit

from mcp_nixos.clients.elasticsearch_client import FIELD_OPT_NAME, FIELD_TYPE  # Import constants used in tests

# Import the server module functions and classes
from mcp_nixos.server import ElasticsearchClient, NixOSContext
from mcp_nixos.tools.nixos_tools import nixos_info, nixos_search

logging.disable(logging.CRITICAL)


class TestServicePathDetection(unittest.TestCase):
    """Test detection and special handling of service paths."""

    def test_is_service_path_detection(self):
        """Test the detection of service paths."""

        # Setup - extract the service path detection logic from mcp_nixos.server.py's nixos_search function
        def is_service_path(query):
            return query.startswith("services.") if not query.startswith("*") else False

        # Test positive cases
        self.assertTrue(is_service_path("services.postgresql"))
        self.assertTrue(is_service_path("services.nginx.enable"))
        self.assertTrue(is_service_path("services.apache.virtualHosts"))

        # Test negative cases
        self.assertFalse(is_service_path("*services.postgresql"))
        self.assertFalse(is_service_path("system.stateVersion"))
        self.assertFalse(is_service_path("boot.loader.grub"))
        self.assertFalse(is_service_path("environment.variables"))

    def test_service_name_extraction(self):
        """Test extraction of service name from path."""

        # Setup - extract the service name extraction logic from mcp_nixos.server.py's nixos_search function
        def extract_service_name(query):
            if not query.startswith("services."):
                return ""
            service_parts = query.split(".", 2)
            return service_parts[1] if len(service_parts) > 1 else ""

        # Test valid service paths
        self.assertEqual(extract_service_name("services.postgresql"), "postgresql")
        self.assertEqual(extract_service_name("services.nginx.enable"), "nginx")
        self.assertEqual(extract_service_name("services.apache.virtualHosts.default"), "apache")

        # Test edge cases
        self.assertEqual(extract_service_name("services."), "")
        self.assertEqual(extract_service_name("non-service-path"), "")


# Modify TestServiceOptionSearchReal to use mocks instead of real API
class TestServiceOptionSearchMocked(unittest.TestCase):  # Renamed and changed base class
    """Test service option search with mocked API calls."""

    @patch.object(ElasticsearchClient, "safe_elasticsearch_query")
    def test_search_hierarchical_path_structure(self, mock_safe_query):
        """Test that our search query builder handles hierarchical paths correctly."""
        # Configure the mock to return a simulated successful response
        mock_safe_query.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_score": 10.0,  # Add score for parsing logic
                        "_source": {
                            FIELD_OPT_NAME: "services.nginx.enable",
                            "option_description": "Enable nginx",
                            FIELD_TYPE: "option",  # Ensure type is correct
                            "option_type": "boolean",  # Add option_type for parsing
                        },
                    }
                ],
            }
        }

        client = ElasticsearchClient()
        # Ensure the client uses the unstable channel for consistency with the mock data
        client.set_channel("unstable")

        # Test the internal search_options method with a service path
        # This will now use the mocked safe_elasticsearch_query
        result = client.search_options("services.nginx", limit=5)

        # 1. Verify the query sent to Elasticsearch (most important)
        mock_safe_query.assert_called_once()
        args, kwargs = mock_safe_query.call_args
        endpoint_url, query_data = args  # Endpoint is first arg, query_data is second
        self.assertIn("unstable", endpoint_url)  # Verify correct channel URL
        self.assertIn("query", query_data)
        query = query_data["query"]

        # Check query structure robustly
        self.assertIn("bool", query)
        self.assertIn("must", query["bool"])
        self.assertIn("filter", query["bool"])

        # Check specific clauses
        query_str = json.dumps(query)  # Use for checking specific values easily
        self.assertIn('"prefix": {"option_name": {"value": "services.nginx"', query_str)
        self.assertIn('"wildcard": {"option_name": {"value": "services.nginx.*"', query_str)
        self.assertIn('"wildcard": {"option_name": {"value": "services.nginx*"', query_str)

        # Check filter structure more robustly instead of exact string match
        expected_filter = [{"term": {FIELD_TYPE: "option"}}]
        self.assertTrue(
            any(f == expected_filter[0] for f in query["bool"].get("filter", [])),
            f"Filter {query['bool'].get('filter')} does not contain {expected_filter[0]}",
        )

        # 2. Verify the processing of the simulated successful response
        self.assertNotIn("error", result)
        self.assertIn("options", result)
        self.assertIn("count", result)
        self.assertIsInstance(result["options"], list)
        self.assertEqual(result["count"], 1)  # Based on mock response total
        self.assertEqual(len(result["options"]), 1)  # Based on mock response hits

        # Verify the content matches the mock response hit (using _parse_hits)
        self.assertEqual(result["options"][0]["name"], "services.nginx.enable")
        self.assertEqual(result["options"][0]["description"], "Enable nginx")
        self.assertEqual(result["options"][0]["type"], "boolean")  # Check parsed type

    def test_multiple_channels(self):  # This test remains mostly the same
        """Test that channel selection works for service options."""
        client = ElasticsearchClient()

        # Try with unstable channel
        client.set_channel("unstable")
        unstable_url = client.es_options_url  # Check options URL

        # Try with 24.11 channel
        client.set_channel("24.11")
        stable_url = client.es_options_url  # Check options URL

        # Both URLs should be different and contain the correct channel strings
        self.assertIn("unstable", unstable_url)
        self.assertIn("24.11", stable_url)
        self.assertNotEqual(unstable_url, stable_url)

    @patch.object(ElasticsearchClient, "safe_elasticsearch_query")
    def test_get_option_related_options(self, mock_safe_query):
        """Test that get_option returns related options for service paths (Mocked)."""
        # Simulate the two calls: one for the main option, one for related
        mock_safe_query.side_effect = [
            # 1. Response for get_option('services.nginx.enable')
            {
                "hits": {
                    "total": {"value": 1},
                    "hits": [
                        {
                            "_score": 10.0,
                            "_source": {
                                FIELD_OPT_NAME: "services.nginx.enable",
                                "option_description": "Enable nginx",
                                FIELD_TYPE: "option",
                                "option_type": "boolean",
                            },
                        }
                    ],
                }
            },
            # 2. Response for the related options query
            {
                "hits": {
                    "total": {"value": 1},
                    "hits": [
                        {
                            "_score": 9.0,
                            "_source": {
                                FIELD_OPT_NAME: "services.nginx.package",
                                "option_description": "Nginx package",
                                FIELD_TYPE: "option",
                                "option_type": "package",
                            },
                        }
                    ],
                }
            },
        ]

        client = ElasticsearchClient()
        client.set_channel("unstable")

        result = client.get_option("services.nginx.enable")

        # Verify the main option was found
        self.assertTrue(result.get("found", False))
        self.assertEqual(result["name"], "services.nginx.enable")
        self.assertEqual(result["type"], "boolean")  # Check parsed type

        # Verify related options were fetched and included
        self.assertEqual(mock_safe_query.call_count, 2)  # Should make two calls
        self.assertIn("related_options", result)
        self.assertEqual(len(result["related_options"]), 1)
        self.assertEqual(result["related_options"][0]["name"], "services.nginx.package")
        self.assertEqual(result["related_options"][0]["type"], "package")  # Check parsed type
        self.assertTrue(result.get("is_service_path", False))
        self.assertEqual(result.get("service_name"), "nginx")


class TestServiceOptionTools(unittest.TestCase):
    """Test the MCP tools for service options."""

    def setUp(self):
        """Set up the test environment."""
        # We'll simulate the tool behavior but patch the NixOSContext methods
        # to avoid actual API calls while still testing our logic
        self.context = NixOSContext()

        # These patches allow us to test the logic in the tools without real API calls
        patcher1 = patch.object(NixOSContext, "search_options")
        self.mock_search_options = patcher1.start()
        self.addCleanup(patcher1.stop)

        patcher2 = patch.object(NixOSContext, "get_option")
        self.mock_get_option = patcher2.start()
        self.addCleanup(patcher2.stop)

        # Patch the set_channel method on the mocked es_client
        patcher3 = patch.object(ElasticsearchClient, "set_channel")
        self.mock_set_channel = patcher3.start()
        self.addCleanup(patcher3.stop)
        # Add the es_client mock to the context mock
        self.context.es_client = MagicMock()
        self.context.es_client.set_channel = self.mock_set_channel

        # Set up default mock responses
        self.mock_search_options.return_value = {"options": [], "count": 0}
        self.mock_get_option.return_value = {
            "name": "test",
            "found": False,
            "error": "Not found",
        }

    def test_nixos_search_service_path_suggestions(self):
        """Test that the search tool provides helpful suggestions for service paths."""
        # Mock an empty result for a service search to test suggestions
        self.mock_search_options.return_value = {"options": [], "count": 0}

        # Call nixos_search with a service path
        result = nixos_search("services.postgresql", "options", 10, context=self.context)

        # Verify it contains helpful suggestions
        self.assertIn("No options found for 'services.postgresql'", result)
        # The actual message includes "To find options for the 'postgresql' service, try these searches:"
        self.assertIn("try these searches", result.lower())
        self.assertIn("services.postgresql.enable", result)
        self.assertIn("services.postgresql.package", result)

        # Verify the structure of suggestions
        self.assertIn("Or try a more specific option path", result)

    def test_nixos_search_service_path_with_results(self):
        """Test that the search tool formats service path results correctly."""
        # Mock results for a service search
        self.mock_search_options.return_value = {
            "options": [
                {
                    "name": "services.postgresql.enable",
                    "description": "Whether to enable PostgreSQL Server.",
                    "type": "boolean",
                },
                {
                    "name": "services.postgresql.package",
                    "description": "PostgreSQL package to use.",
                    "type": "package",
                },
            ],
            "count": 2,
        }

        # Call nixos_search with a service path
        result = nixos_search("services.postgresql", "options", 10, context=self.context)

        # Verify it contains the results
        self.assertIn("Found 2 options for", result)
        self.assertIn("services.postgresql.enable", result)
        self.assertIn("services.postgresql.package", result)

        # Verify the structured help section is NOT included in search results
        # (It's added by nixos_info)
        self.assertNotIn("Common option patterns for 'postgresql' service", result)

    def test_nixos_info_service_option_found(self):
        """Test that the info tool displays service options correctly."""
        # Mock a found service option with related options
        self.mock_get_option.return_value = {
            "name": "services.postgresql.enable",
            "description": "Whether to enable PostgreSQL Server.",
            "type": "boolean",
            "default": "false",
            "example": "true",
            "found": True,
            "is_service_path": True,
            "service_name": "postgresql",
            "related_options": [
                {
                    "name": "services.postgresql.package",
                    "description": "PostgreSQL package to use.",
                    "type": "package",
                },
                {
                    "name": "services.postgresql.dataDir",
                    "description": "Data directory for PostgreSQL.",
                    "type": "string",
                },
            ],
        }

        # Call nixos_info for the service option
        result = nixos_info("services.postgresql.enable", "option", context=self.context)

        # Verify the result contains the option and related options
        self.assertIn("# services.postgresql.enable", result)
        self.assertIn("**Type:** boolean", result)
        self.assertIn("**Default:**", result)

        # Verify related options section
        self.assertIn("Related Options for postgresql Service", result)
        self.assertIn("services.postgresql.package", result)
        self.assertIn("services.postgresql.dataDir", result)

        # Verify example configuration
        self.assertIn("Example NixOS Configuration", result)
        self.assertIn("# /etc/nixos/configuration.nix", result)
        self.assertIn("services.postgresql = {", result)
        self.assertIn("enable = true;", result)

    def test_nixos_info_service_option_not_found(self):
        """Test that the info tool provides helpful suggestions when service options aren't found."""
        # Mock a not found service option with service path info
        self.mock_get_option.return_value = {
            "name": "services.postgresql.nonexistent",
            "error": "Option not found. Try common patterns like services.postgresql.enable",
            "found": False,
            "is_service_path": True,
            "service_name": "postgresql",
        }

        # Call nixos_info for the non-existent service option
        result = nixos_info("services.postgresql.nonexistent", "option", context=self.context)

        # Verify the result contains helpful suggestions
        self.assertIn("# Option 'services.postgresql.nonexistent' not found", result)
        self.assertIn("Common Options for Services", result)
        self.assertIn("services.postgresql.enable", result)
        self.assertIn("services.postgresql.package", result)

        # Verify example configuration is provided
        self.assertIn("Example NixOS Configuration", result)
        self.assertIn("# Enable postgresql service", result)


@pytest.mark.integration
class TestIntegrationScenarios(unittest.TestCase):
    """Test full integration scenarios with several edge cases."""

    def setUp(self):
        """Set up the test environment."""
        # Patch importlib.import_module to return a mocked server module
        patcher_import = patch("importlib.import_module")
        self.mock_import_module = patcher_import.start()
        self.addCleanup(patcher_import.stop)

        # Create a mock context and server module
        self.mock_context = MagicMock(spec=NixOSContext)
        self.mock_context.es_client = MagicMock(spec=ElasticsearchClient)  # Add mock es_client

        # Create a mock server module that get_nixos_context will return our mock context
        self.mock_server_module = MagicMock()
        self.mock_server_module.get_nixos_context.return_value = self.mock_context
        self.mock_import_module.return_value = self.mock_server_module

    def test_channel_selection_in_service_search(self):
        """Test that channel selection is respected in service searches."""
        # Mock search to return empty results (we're testing channel parameter only)
        self.mock_context.search_options.return_value = {"options": [], "count": 0}

        # Call nixos_search with a channel parameter
        nixos_search("services.postgresql", "options", 10, channel="24.11", context=self.mock_context)

        # Verify the search was called and channel was set on the mocked client
        self.mock_context.search_options.assert_called_once()
        # Verify the context's es_client.set_channel was called
        self.mock_context.es_client.set_channel.assert_called_with("24.11")

    def test_multi_channel_support(self):
        """Test that search supports multiple channels by checking set_channel calls."""
        # Mock search to return empty results
        self.mock_context.search_options.return_value = {"options": [], "count": 0}

        # Test with unstable channel
        nixos_search("services.postgresql", "options", 10, channel="unstable", context=self.mock_context)
        self.mock_context.es_client.set_channel.assert_called_with("unstable")
        self.mock_context.es_client.set_channel.reset_mock()  # Reset for next call

        # Test with 24.11 channel
        nixos_search("services.postgresql", "options", 10, channel="24.11", context=self.mock_context)
        self.mock_context.es_client.set_channel.assert_called_with("24.11")
        self.mock_context.es_client.set_channel.reset_mock()

        # Test with invalid channel (ElasticsearchClient handles fallback internally)
        nixos_search("services.postgresql", "options", 10, channel="invalid", context=self.mock_context)
        # The tool passes 'invalid' to set_channel; the client handles the fallback.
        self.mock_context.es_client.set_channel.assert_called_with("invalid")

    def test_option_hierarchy_pattern_examples(self):
        """Test that info shows appropriate examples for different option types."""
        # Test boolean option
        self.mock_context.get_option.return_value = {
            "name": "services.postgresql.enable",
            "type": "boolean",
            "found": True,
            "is_service_path": True,
            "service_name": "postgresql",
            "related_options": [],
            "example": "true",  # Add the missing example field
        }
        result_bool = nixos_info("services.postgresql.enable", "option", context=self.mock_context)
        self.assertIn("boolean", result_bool)
        # Check the "Example in context" block specifically
        self.assertIn("**Example in context:**", result_bool)
        self.assertIn("enable = true;", result_bool)  # Verify the line exists within the context example

        # Test string option
        self.mock_context.get_option.return_value = {
            "name": "services.postgresql.dataDir",
            "type": "string",
            "found": True,
            "is_service_path": True,
            "service_name": "postgresql",
            "related_options": [],
            "default": '"/var/lib/postgresql"',
            "example": '"/custom/path"',  # Add example
        }
        result_str = nixos_info("services.postgresql.dataDir", "option", context=self.mock_context)
        self.assertIn("string", result_str)
        # Check the "Example in context" block specifically
        self.assertIn("**Example in context:**", result_str)

        # More robust check for string example line
        expected_line1 = 'dataDir = "/path/to/value";'  # Placeholder used by corrected formatter
        expected_line2 = 'dataDir = "/custom/path";'  # Example value from mock data
        # Find the actual line generated in the context block
        context_example_block_search = result_str.split("**Example in context:**")
        self.assertEqual(len(context_example_block_search), 2, "Context example block not found or malformed")
        context_example_code = context_example_block_search[1].split("```")[1]  # Get code between ```
        actual_dataDir_line = [line for line in context_example_code.split("\n") if "dataDir =" in line]

        # Allow either the placeholder or the actual example value
        self.assertTrue(
            actual_dataDir_line
            and (expected_line1 in actual_dataDir_line[0] or expected_line2 in actual_dataDir_line[0]),
            # Updated error message to be slightly shorter and fit within 120 chars
            f"Expected '{expected_line1}' or '{expected_line2}' in context example, "
            f"but got line: {actual_dataDir_line}",
        )

        # Test integer option
        self.mock_context.get_option.return_value = {
            "name": "services.postgresql.port",
            "type": "int",
            "found": True,
            "is_service_path": True,
            "service_name": "postgresql",
            "related_options": [],
            "example": "5433",  # Add example
        }
        result_int = nixos_info("services.postgresql.port", "option", context=self.mock_context)
        self.assertIn("int", result_int)
        # Check the "Example in context" block specifically
        self.assertIn("**Example in context:**", result_int)
        # Check for potential numeric values without quotes
        self.assertTrue("port = 1234;" in result_int or "port = 5432;" in result_int or "port = 5433;" in result_int)


if __name__ == "__main__":
    unittest.main()
