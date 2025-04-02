"""Test the nix-darwin resources for MCP."""

import logging
import unittest
import pytest
from unittest.mock import Mock, patch

# Mark as unit tests
pytestmark = pytest.mark.unit

# Import base test class
from tests import MCPNixOSTestBase

# Import the resource functions directly from the resources module
from mcp_nixos.resources.darwin.darwin_resources import (
    get_darwin_status,
    search_darwin_options,
    get_darwin_option,
    get_darwin_statistics,
    get_darwin_categories,
    get_darwin_options_by_prefix,
    # Category-specific functions
    get_darwin_documentation_options,
    get_darwin_environment_options,
    get_darwin_fonts_options,
    get_darwin_homebrew_options,
    get_darwin_launchd_options,
    get_darwin_networking_options,
    get_darwin_nix_options,
    get_darwin_nixpkgs_options,
    get_darwin_power_options,
    get_darwin_programs_options,
    get_darwin_security_options,
    get_darwin_services_options,
    get_darwin_system_options,
    get_darwin_time_options,
    get_darwin_users_options,
    _get_options_by_category,
)

# Disable logging during tests
logging.disable(logging.CRITICAL)


class TestDarwinResourceEndpoints(MCPNixOSTestBase):
    """Test the nix-darwin MCP resource endpoints."""

    def setUp(self):
        """Set up the test environment."""
        # Create a mock for the DarwinContext
        self.mock_context = Mock()

    def test_get_darwin_status(self):
        """Test the get_darwin_status function."""
        expected_status = {
            "status": "ok",
            "loaded": True,
            "options_count": 1234,
            "categories_count": 42,
            "cache_stats": {
                "size": 50,
                "max_size": 100,
                "ttl": 86400,
                "hits": 100,
                "misses": 20,
                "hit_ratio": 0.83,
            },
        }
        self.mock_context.get_status.return_value = expected_status

        result = get_darwin_status(self.mock_context)

        self.assertEqual(result, expected_status)
        self.mock_context.get_status.assert_called_once()

    def test_get_darwin_status_error(self):
        """Test the get_darwin_status function when an error occurs."""
        self.mock_context.get_status.side_effect = Exception("Test error")

        result = get_darwin_status(self.mock_context)

        self.assertIn("error", result)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["options_count"], 0)
        self.assertEqual(result["categories_count"], 0)
        self.mock_context.get_status.assert_called_once()

    def test_get_darwin_status_no_context(self):
        """Test the get_darwin_status function with no context."""
        with patch("mcp_nixos.resources.darwin.darwin_resources.get_context_or_fallback", return_value=None):
            result = get_darwin_status()

        self.assertIn("error", result)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["options_count"], 0)
        self.assertEqual(result["categories_count"], 0)

    def test_search_darwin_options(self):
        """Test the search_darwin_options function."""
        expected_search_result = {
            "query": "networking",
            "limit": 20,
            "count": 2,
            "results": [
                {
                    "name": "networking.hostName",
                    "type": "string",
                    "description": "The hostname for this machine.",
                },
                {
                    "name": "networking.firewall.enable",
                    "type": "boolean",
                    "description": "Whether to enable the firewall.",
                },
            ],
            "found": True,
        }
        self.mock_context.search_options.return_value = expected_search_result["results"]

        result = search_darwin_options("networking", context=self.mock_context)

        self.assertEqual(result, expected_search_result)
        self.mock_context.search_options.assert_called_once_with("networking", limit=20)

    def test_search_darwin_options_empty_results(self):
        """Test the search_darwin_options function with empty results."""
        self.mock_context.search_options.return_value = []

        result = search_darwin_options("nonexistent", context=self.mock_context)

        self.assertEqual(result["query"], "nonexistent")
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["results"], [])
        self.assertEqual(result["found"], False)
        self.mock_context.search_options.assert_called_once_with("nonexistent", limit=20)

    def test_search_darwin_options_error(self):
        """Test the search_darwin_options function when an error occurs."""
        self.mock_context.search_options.side_effect = Exception("Test error")

        result = search_darwin_options("test", context=self.mock_context)

        self.assertIn("error", result)
        self.assertEqual(result["query"], "test")
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["results"], [])
        self.assertEqual(result["found"], False)
        self.mock_context.search_options.assert_called_once_with("test", limit=20)

    def test_search_darwin_options_no_context(self):
        """Test the search_darwin_options function with no context."""
        with patch("mcp_nixos.resources.darwin.darwin_resources.get_context_or_fallback", return_value=None):
            result = search_darwin_options("test")

        self.assertIn("error", result)
        self.assertEqual(result["query"], "test")
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["results"], [])
        self.assertEqual(result["found"], False)

    def test_get_darwin_option(self):
        """Test the get_darwin_option function."""
        expected_option = {
            "name": "networking.hostName",
            "type": "string",
            "description": "The hostname for this machine.",
            "default": "darwin",
            "example": "mymac",
            "related_options": ["networking.firewall.enable"],
        }
        self.mock_context.get_option.return_value = expected_option

        result = get_darwin_option("networking.hostName", context=self.mock_context)

        self.assertEqual(result["name"], "networking.hostName")
        self.assertEqual(result["option"], expected_option)
        self.assertEqual(result["found"], True)
        self.mock_context.get_option.assert_called_once_with("networking.hostName")

    def test_get_darwin_option_not_found(self):
        """Test the get_darwin_option function when option is not found."""
        self.mock_context.get_option.return_value = None

        result = get_darwin_option("nonexistent.option", context=self.mock_context)

        self.assertIn("error", result)
        self.assertEqual(result["name"], "nonexistent.option")
        self.assertEqual(result["found"], False)
        self.mock_context.get_option.assert_called_once_with("nonexistent.option")

    def test_get_darwin_option_error(self):
        """Test the get_darwin_option function when an error occurs."""
        self.mock_context.get_option.side_effect = Exception("Test error")

        result = get_darwin_option("test.option", context=self.mock_context)

        self.assertIn("error", result)
        self.assertEqual(result["name"], "test.option")
        self.assertEqual(result["found"], False)
        self.mock_context.get_option.assert_called_once_with("test.option")

    def test_get_darwin_option_no_context(self):
        """Test the get_darwin_option function with no context."""
        with patch("mcp_nixos.resources.darwin.darwin_resources.get_context_or_fallback", return_value=None):
            result = get_darwin_option("test.option")

        self.assertIn("error", result)
        self.assertEqual(result["name"], "test.option")
        self.assertEqual(result["found"], False)

    def test_get_darwin_statistics(self):
        """Test the get_darwin_statistics function."""
        expected_stats = {
            "total_options": 1234,
            "by_category": {
                "networking": 50,
                "programs": 200,
                "system": 150,
            },
            "by_type": {
                "boolean": 500,
                "string": 400,
                "integer": 150,
                "list": 100,
                "attribute set": 84,
            },
        }
        self.mock_context.get_statistics.return_value = expected_stats

        result = get_darwin_statistics(context=self.mock_context)

        self.assertEqual(result["statistics"], expected_stats)
        self.assertEqual(result["found"], True)
        self.mock_context.get_statistics.assert_called_once()

    def test_get_darwin_statistics_error(self):
        """Test the get_darwin_statistics function when an error occurs."""
        self.mock_context.get_statistics.side_effect = Exception("Test error")

        result = get_darwin_statistics(context=self.mock_context)

        self.assertIn("error", result)
        self.assertEqual(result["found"], False)
        self.mock_context.get_statistics.assert_called_once()

    def test_get_darwin_statistics_no_context(self):
        """Test the get_darwin_statistics function with no context."""
        with patch("mcp_nixos.resources.darwin.darwin_resources.get_context_or_fallback", return_value=None):
            result = get_darwin_statistics()

        self.assertIn("error", result)
        self.assertEqual(result["found"], False)

    def test_get_darwin_categories(self):
        """Test the get_darwin_categories function."""
        expected_categories = [
            {"name": "networking", "count": 50},
            {"name": "programs", "count": 200},
            {"name": "system", "count": 150},
        ]
        self.mock_context.get_categories.return_value = expected_categories

        result = get_darwin_categories(context=self.mock_context)

        self.assertEqual(result["categories"], expected_categories)
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["found"], True)
        self.mock_context.get_categories.assert_called_once()

    def test_get_darwin_categories_error(self):
        """Test the get_darwin_categories function when an error occurs."""
        self.mock_context.get_categories.side_effect = Exception("Test error")

        result = get_darwin_categories(context=self.mock_context)

        self.assertIn("error", result)
        self.assertEqual(result["categories"], [])
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["found"], False)
        self.mock_context.get_categories.assert_called_once()

    def test_get_darwin_categories_no_context(self):
        """Test the get_darwin_categories function with no context."""
        with patch("mcp_nixos.resources.darwin.darwin_resources.get_context_or_fallback", return_value=None):
            result = get_darwin_categories()

        self.assertIn("error", result)
        self.assertEqual(result["categories"], [])
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["found"], False)

    def test_get_darwin_options_by_prefix(self):
        """Test the get_darwin_options_by_prefix function."""
        expected_options = [
            {
                "name": "networking.hostName",
                "type": "string",
                "description": "The hostname for this machine.",
            },
            {
                "name": "networking.firewall.enable",
                "type": "boolean",
                "description": "Whether to enable the firewall.",
            },
        ]
        self.mock_context.get_options_by_prefix.return_value = expected_options

        result = get_darwin_options_by_prefix("networking", context=self.mock_context)

        self.assertEqual(result["prefix"], "networking")
        self.assertEqual(result["options"], expected_options)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["found"], True)
        self.mock_context.get_options_by_prefix.assert_called_once_with("networking")

    def test_get_darwin_options_by_prefix_empty_results(self):
        """Test the get_darwin_options_by_prefix function with empty results."""
        self.mock_context.get_options_by_prefix.return_value = []

        result = get_darwin_options_by_prefix("nonexistent", context=self.mock_context)

        self.assertEqual(result["prefix"], "nonexistent")
        self.assertEqual(result["options"], [])
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["found"], False)
        self.mock_context.get_options_by_prefix.assert_called_once_with("nonexistent")

    def test_get_darwin_options_by_prefix_error(self):
        """Test the get_darwin_options_by_prefix function when an error occurs."""
        self.mock_context.get_options_by_prefix.side_effect = Exception("Test error")

        result = get_darwin_options_by_prefix("test", context=self.mock_context)

        self.assertIn("error", result)
        self.assertEqual(result["prefix"], "test")
        self.assertEqual(result["options"], [])
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["found"], False)
        self.mock_context.get_options_by_prefix.assert_called_once_with("test")

    def test_get_darwin_options_by_prefix_no_context(self):
        """Test the get_darwin_options_by_prefix function with no context."""
        with patch("mcp_nixos.resources.darwin.darwin_resources.get_context_or_fallback", return_value=None):
            result = get_darwin_options_by_prefix("test")

        self.assertIn("error", result)
        self.assertEqual(result["prefix"], "test")
        self.assertEqual(result["options"], [])
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["found"], False)

    def test_get_options_by_category_helper(self):
        """Test the _get_options_by_category helper function."""
        # Mock get_darwin_options_by_prefix to verify it's called correctly
        with patch("mcp_nixos.resources.darwin.darwin_resources.get_darwin_options_by_prefix") as mock_get_prefix:
            mock_get_prefix.return_value = {"prefix": "test", "options": [], "count": 0}

            result = _get_options_by_category("test", context=self.mock_context)

            mock_get_prefix.assert_called_once_with("test", self.mock_context)
            self.assertEqual(result, {"prefix": "test", "options": [], "count": 0})

    def test_category_specific_functions(self):
        """Test all category-specific resource functions."""

        # Create a helper to test each category function
        def test_category_function(func, category):
            with patch("mcp_nixos.resources.darwin.darwin_resources._get_options_by_category") as mock_get_cat:
                mock_get_cat.return_value = {"prefix": category, "options": [], "count": 0}

                result = func(context=self.mock_context)

                mock_get_cat.assert_called_once_with(category, self.mock_context)
                self.assertEqual(result, {"prefix": category, "options": [], "count": 0})

        # Test each category function
        test_category_function(get_darwin_documentation_options, "documentation")
        test_category_function(get_darwin_environment_options, "environment")
        test_category_function(get_darwin_fonts_options, "fonts")
        test_category_function(get_darwin_homebrew_options, "homebrew")
        test_category_function(get_darwin_launchd_options, "launchd")
        test_category_function(get_darwin_networking_options, "networking")
        test_category_function(get_darwin_nix_options, "nix")
        test_category_function(get_darwin_nixpkgs_options, "nixpkgs")
        test_category_function(get_darwin_power_options, "power")
        test_category_function(get_darwin_programs_options, "programs")
        test_category_function(get_darwin_security_options, "security")
        test_category_function(get_darwin_services_options, "services")
        test_category_function(get_darwin_system_options, "system")
        test_category_function(get_darwin_time_options, "time")
        test_category_function(get_darwin_users_options, "users")


if __name__ == "__main__":
    unittest.main()
