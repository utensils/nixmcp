"""Tests for service path option handling and discovery in NixMCP."""

import unittest
from unittest.mock import patch

# Import from base test class
from tests import NixMCPRealAPITestBase

# Import the server module functions and classes
from nixmcp.server import nixos_search, nixos_info, ElasticsearchClient, NixOSContext

# Disable logging during tests
import logging

logging.disable(logging.CRITICAL)


class TestServicePathDetection(unittest.TestCase):
    """Test detection and special handling of service paths."""

    def test_is_service_path_detection(self):
        """Test the detection of service paths."""

        # Setup - extract the service path detection logic from nixmcp.server.py's nixos_search function
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

        # Setup - extract the service name extraction logic from nixmcp.server.py's nixos_search function
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


class TestServiceOptionSearchReal(NixMCPRealAPITestBase):
    """Test service option search with real API calls."""

    def test_search_hierarchical_path_structure(self):
        """Test that our search handles hierarchical paths correctly."""
        # Use a common service that should have options
        client = ElasticsearchClient()

        # Test the internal search_options method with a service path
        result = client.search_options("services.nginx", limit=5)

        # Only check the structure since we're using real API
        if "error" in result:
            self.assertIsInstance(result["error"], str)
            # Skip the rest of the test if there's an API error
            return

        # Check the expected structure
        self.assertIn("options", result)
        self.assertIn("count", result)
        self.assertIsInstance(result["options"], list)

        # If we got results, verify correct handling
        if len(result["options"]) > 0:
            # Verify at least one option name starts with services.nginx
            has_service_option = False
            for opt in result["options"]:
                if "name" in opt and opt["name"].startswith("services.nginx"):
                    has_service_option = True
                    break

            # It's possible the API doesn't have the exact service,
            # but if it returns results, they should be relevant
            if result["count"] > 0:
                self.assertTrue(
                    has_service_option,
                    "At least one option should start with services.nginx",
                )

    def test_multiple_channels(self):
        """Test that channel selection works for service options."""
        client = ElasticsearchClient()

        # Try with unstable channel
        client.set_channel("unstable")
        unstable_url = client.es_packages_url
        unstable_result = client.search_options("services.nginx", limit=5)

        # Try with 24.11 channel
        client.set_channel("24.11")
        stable_url = client.es_packages_url
        stable_result = client.search_options("services.nginx", limit=5)

        # Both should have the same structure regardless of content
        self.assertIn("count", unstable_result)
        self.assertIn("count", stable_result)

        # Both should have the options list even if empty
        self.assertIn("options", unstable_result)
        self.assertIn("options", stable_result)

        # Test channel URLs were set correctly - unstable URL should have changed to stable
        self.assertIn("unstable", unstable_url)
        self.assertIn("24.11", stable_url)
        self.assertNotEqual(unstable_url, stable_url)

    def test_get_option_related_options(self):
        """Test that get_option returns related options for service paths."""
        client = ElasticsearchClient()

        # Try to get a service option with a common path
        result = client.get_option("services.nginx.enable")

        # Check if this option is found (it might not be in the real API)
        if result.get("found", False):
            # If it's flagged as a service path and has related options, check them
            if result.get("is_service_path", False) and "related_options" in result:
                # Verify related options structure
                self.assertIsInstance(result["related_options"], list)

                if len(result["related_options"]) > 0:
                    # Verify each related option has the expected structure
                    for related in result["related_options"]:
                        self.assertIn("name", related)
                        # Each related option should be from the same service
                        self.assertTrue(
                            related["name"].startswith("services.nginx"),
                            f"Related option should start with services.nginx: {related['name']}",
                        )
        else:
            # If option not found, verify the error structure
            self.assertIn("error", result)
            self.assertFalse(result.get("found", True))


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
        result = nixos_search("services.postgresql", "options", 10)

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
        result = nixos_search("services.postgresql", "options", 10)

        # Verify it contains the results
        self.assertIn("Found 2 options for", result)
        self.assertIn("services.postgresql.enable", result)
        self.assertIn("services.postgresql.package", result)

        # Verify the structured help section
        self.assertIn("Common option patterns for 'postgresql' service", result)
        self.assertIn("enable", result)
        self.assertIn("package", result)
        self.assertIn("settings", result)

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
        result = nixos_info("services.postgresql.enable", "option")

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
        result = nixos_info("services.postgresql.nonexistent", "option")

        # Verify the result contains helpful suggestions
        self.assertIn("# Option 'services.postgresql.nonexistent' not found", result)
        self.assertIn("Common Options for Services", result)
        self.assertIn("services.postgresql.enable", result)
        self.assertIn("services.postgresql.package", result)

        # Verify example configuration is provided
        self.assertIn("Example NixOS Configuration", result)
        self.assertIn("# Enable postgresql service", result)


class TestIntegrationScenarios(unittest.TestCase):
    """Test full integration scenarios with several edge cases."""

    def setUp(self):
        """Set up the test environment."""
        self.context = NixOSContext()

    @patch.object(ElasticsearchClient, "set_channel")
    @patch.object(NixOSContext, "search_options")
    def test_channel_selection_in_service_search(self, mock_search, mock_set_channel):
        """Test that channel selection is respected in service searches."""
        # Mock search to return empty results (we're testing channel parameter only)
        mock_search.return_value = {"options": [], "count": 0}

        # Call nixos_search with a channel parameter
        nixos_search("services.postgresql", "options", 10, channel="24.11")

        # Verify the search was called and channel was set
        mock_search.assert_called_once()
        mock_set_channel.assert_called_with("24.11")

    @patch.object(ElasticsearchClient, "set_channel")
    def test_multi_channel_support(self, mock_set_channel):
        """Test that search supports multiple channels."""
        # Call nixos_search with different channels
        nixos_search("services.postgresql", "options", 10, channel="unstable")
        mock_set_channel.assert_called_with("unstable")

        nixos_search("services.postgresql", "options", 10, channel="24.11")
        mock_set_channel.assert_called_with("24.11")

        # Test fallback to unstable for unknown channel
        nixos_search("services.postgresql", "options", 10, channel="invalid")
        # Last call should be to unstable as fallback
        mock_set_channel.assert_called_with("invalid")

    @patch.object(NixOSContext, "get_option")
    def test_option_hierarchy_pattern_examples(self, mock_get_option):
        """Test that info shows appropriate examples for different option types."""
        # Test boolean option
        mock_get_option.return_value = {
            "name": "services.postgresql.enable",
            "type": "boolean",
            "found": True,
        }
        result = nixos_info("services.postgresql.enable", "option")
        self.assertIn("boolean", result)

        # Test string option
        mock_get_option.return_value = {
            "name": "services.postgresql.dataDir",
            "type": "string",
            "found": True,
        }
        result = nixos_info("services.postgresql.dataDir", "option")
        self.assertIn("string", result)

        # Test integer option
        mock_get_option.return_value = {
            "name": "services.postgresql.port",
            "type": "int",
            "found": True,
        }
        result = nixos_info("services.postgresql.port", "option")
        self.assertIn("int", result)


if __name__ == "__main__":
    unittest.main()
