"""Tests for suggestion and error handling in MCP-NixOS."""

# Disable logging during tests
import logging
import unittest
import pytest
from unittest.mock import patch

# Mark as unit tests
pytestmark = pytest.mark.unit

# Import the server module functions and classes
from mcp_nixos.server import ElasticsearchClient, NixOSContext
from mcp_nixos.tools.nixos_tools import nixos_info, nixos_search

logging.disable(logging.CRITICAL)


class TestNotFoundSuggestions(unittest.TestCase):
    """Test suggestions provided when options are not found."""

    def setUp(self):
        """Set up the test environment."""
        # We'll simulate the tool behavior but patch the NixOSContext methods
        self.context = NixOSContext()

        # These patches allow us to test the logic in the tools without real API calls
        patcher1 = patch.object(NixOSContext, "search_options")
        self.mock_search_options = patcher1.start()
        self.addCleanup(patcher1.stop)

        patcher2 = patch.object(NixOSContext, "get_option")
        self.mock_get_option = patcher2.start()
        self.addCleanup(patcher2.stop)

        # Set up default mock responses for "not found" scenarios
        self.mock_search_options.return_value = {"options": [], "count": 0}
        self.mock_get_option.return_value = {
            "name": "test",
            "found": False,
            "error": "Not found",
        }

    def test_service_not_found_suggestions(self):
        """Test suggestions when a service path returns no options."""
        # Mock an empty result for a service search
        self.mock_search_options.return_value = {"options": [], "count": 0}

        # Call nixos_search with a service path
        result = nixos_search("services.nonexistent", "options", 10)

        # Verify it contains helpful suggestions
        self.assertIn("No options found", result)
        self.assertIn("services.nonexistent.enable", result)
        self.assertIn("services.nonexistent.package", result)

        # Check for specific suggestions for common option patterns
        self.assertTrue(any("enable" in line for line in result.split("\n")))
        self.assertTrue(any("package" in line for line in result.split("\n")))
        self.assertTrue(any("settings" in line for line in result.split("\n")))

    def test_option_not_found_specific_suggestions(self):
        """Test that suggestions for not found options are specific to the service."""
        # Mock a not found service option
        self.mock_get_option.return_value = {
            "name": "services.redis.nonexistent",
            "error": "Option not found",
            "found": False,
            "is_service_path": True,
            "service_name": "redis",
        }

        # Call nixos_info for the non-existent option
        result = nixos_info("services.redis.nonexistent", "option")

        # Verify redis-specific suggestions
        self.assertIn("services.redis.enable", result)
        self.assertIn("services.redis.package", result)

        # Check for NixOS configuration example
        self.assertIn("configuration.nix", result)
        self.assertIn("services.redis = {", result)

    def test_specific_option_suggestions_based_on_service(self):
        """Test that suggestions are customized for the specific service."""
        # Test with PostgreSQL
        self.mock_search_options.return_value = {"options": [], "count": 0}
        postgresql_result = nixos_search("services.postgresql", "options", 10)
        self.assertIn("services.postgresql.enable", postgresql_result)

        # Test with Nginx
        nginx_result = nixos_search("services.nginx", "options", 10)
        self.assertIn("services.nginx.enable", nginx_result)

        # Test with systemd
        systemd_result = nixos_search("services.systemd", "options", 10)
        self.assertIn("services.systemd", systemd_result)

        # Ensure each contains the appropriate service name
        self.assertIn("postgresql", postgresql_result)
        self.assertIn("nginx", nginx_result)
        self.assertIn("systemd", systemd_result)


class TestConfigurationExamples(unittest.TestCase):
    """Test the generation of NixOS configuration examples."""

    def setUp(self):
        """Set up the test environment."""
        self.context = NixOSContext()

        # Patch get_option to avoid real API calls
        patcher = patch.object(NixOSContext, "get_option")
        self.mock_get_option = patcher.start()
        self.addCleanup(patcher.stop)

    def test_boolean_option_example(self):
        """Test example generation for boolean options."""
        # Mock a boolean option with related options to trigger example generation
        self.mock_get_option.return_value = {
            "name": "services.postgresql.enable",
            "description": "Whether to enable PostgreSQL Server.",
            "type": "boolean",
            "default": "false",
            "found": True,
            "is_service_path": True,
            "service_name": "postgresql",
            "related_options": [
                {"name": "services.postgresql.package", "type": "package"},
                {"name": "services.postgresql.dataDir", "type": "string"},
            ],
        }

        # Call nixos_info
        result = nixos_info("services.postgresql.enable", "option")

        # Verify the example shows proper boolean setting
        self.assertIn("enable = true;", result)

    def test_string_option_example(self):
        """Test example generation for string options."""
        # Mock a string option with related options
        self.mock_get_option.return_value = {
            "name": "services.postgresql.dataDir",
            "description": "Data directory for PostgreSQL.",
            "type": "string",
            "default": '"/var/lib/postgresql"',
            "found": True,
            "is_service_path": True,
            "service_name": "postgresql",
            "related_options": [
                {"name": "services.postgresql.enable", "type": "boolean"},
                {"name": "services.postgresql.package", "type": "package"},
            ],
        }

        # Call nixos_info
        result = nixos_info("services.postgresql.dataDir", "option")

        # Verify the example shows proper string setting
        self.assertIn("dataDir = ", result)
        self.assertIn('"', result)  # Should have quotes for string values

    def test_int_option_example(self):
        """Test example generation for integer options."""
        # Mock an integer option with related options
        self.mock_get_option.return_value = {
            "name": "services.postgresql.port",
            "description": "Port for PostgreSQL.",
            "type": "int",
            "default": "5432",
            "found": True,
            "is_service_path": True,
            "service_name": "postgresql",
            "related_options": [
                {"name": "services.postgresql.enable", "type": "boolean"},
                {"name": "services.postgresql.package", "type": "package"},
            ],
        }

        # Call nixos_info
        result = nixos_info("services.postgresql.port", "option")

        # Verify the example shows proper int setting (no quotes)
        self.assertIn("port = ", result)
        line_with_port = [line for line in result.split("\n") if "port = " in line][0]
        self.assertTrue(
            "port = 1234;" in line_with_port or "port = 5432;" in line_with_port,
            f"Expected numeric port value, got: {line_with_port}",
        )


class TestHelpfulErrorMessages(unittest.TestCase):
    """Test that error messages provide helpful guidance."""

    def setUp(self):
        """Set up the test environment."""
        self.client = ElasticsearchClient()

        # Patch safe_elasticsearch_query to return errors
        patcher = patch.object(ElasticsearchClient, "safe_elasticsearch_query")
        self.mock_query = patcher.start()
        self.addCleanup(patcher.stop)

    def test_connection_error_message(self):
        """Test that connection errors provide helpful guidance."""
        # Mock a connection error
        self.mock_query.return_value = {"error": "Failed to connect to Elasticsearch"}

        # Try searching
        result = self.client.search_options("services.postgresql")

        # Check error message
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Failed to connect to Elasticsearch")

    def test_option_not_found_message(self):
        """Test that option not found messages are informative."""
        # First set up the mock to return empty hits
        self.mock_query.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

        # Try getting an option
        result = self.client.get_option("services.nonexistent.option")

        # Check error message
        self.assertIn("error", result)
        self.assertFalse(result["found"])

        # If it's a service path, should contain info about that
        if "is_service_path" in result and result["is_service_path"]:
            self.assertIn("service_name", result)
            self.assertIn("Try common patterns", result["error"])


class TestRelatedOptionsDiscovery(unittest.TestCase):
    """Test the discovery of related options for service paths."""

    def setUp(self):
        """Set up the test environment."""
        self.client = ElasticsearchClient()

        # Patch safe_elasticsearch_query to control the response
        patcher = patch.object(ElasticsearchClient, "safe_elasticsearch_query")
        self.mock_query = patcher.start()
        self.addCleanup(patcher.stop)

    def test_related_options_query_structure(self):
        """Test that the query for related options is structured correctly."""
        # Set up mock to return a valid option first
        self.mock_query.side_effect = [
            # First call - return the main option
            {
                "hits": {
                    "total": {"value": 1},
                    "hits": [
                        {
                            "_source": {
                                "option_name": "services.postgresql.enable",
                                "option_description": "Enable PostgreSQL",
                                "type": "option",
                            }
                        }
                    ],
                }
            },
            # Second call - would be for related options
            {"hits": {"hits": [], "total": {"value": 0}}},
        ]

        # Get the option
        self.client.get_option("services.postgresql.enable")

        # Check that a second query was made for related options
        self.assertEqual(self.mock_query.call_count, 2)

        # Get the second query (for related options)
        args, kwargs = self.mock_query.call_args_list[1]
        query_data = kwargs.get("query_data", args[1] if len(args) > 1 else None)

        # Verify correct query structure for related options
        self.assertIsNotNone(query_data)
        self.assertIn("query", query_data)
        self.assertIn("bool", query_data["query"])
        self.assertIn("must", query_data["query"]["bool"])

        # Should have a prefix query for the service path
        must_clauses = query_data["query"]["bool"]["must"]
        has_prefix = any("prefix" in str(clause) for clause in must_clauses)
        self.assertTrue(has_prefix, "Related options query should use prefix matching")

        # Should also have a must_not to exclude the current option
        self.assertIn("must_not", query_data["query"]["bool"])


if __name__ == "__main__":
    unittest.main()
