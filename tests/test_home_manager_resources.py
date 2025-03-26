"""Test Home Manager resource endpoints."""

import logging
from unittest.mock import Mock

# Import base test class
from tests import NixMCPTestBase

# Import the resource functions directly from the resources module
from nixmcp.resources.home_manager_resources import (
    home_manager_status_resource,
    home_manager_search_options_resource,
    home_manager_option_resource,
    home_manager_stats_resource,
    home_manager_options_list_resource,
    home_manager_options_by_prefix_resource,
)

# Disable logging during tests
logging.disable(logging.CRITICAL)


class TestHomeManagerResourceEndpoints(NixMCPTestBase):
    """Test the Home Manager MCP resource endpoints."""

    def setUp(self):
        """Set up the test environment."""
        # Create a mock for the HomeManagerContext
        self.mock_context = Mock()

    def test_status_resource(self):
        """Test the home-manager://status resource."""
        # Mock the get_status method
        self.mock_context.get_status.return_value = {
            "status": "ok",
            "loaded": True,
            "options_count": 1234,
            "cache_stats": {
                "hits": 100,
                "misses": 20,
                "hit_ratio": 0.83,
            },
        }

        # Call the resource function with our mock context
        result = home_manager_status_resource(self.mock_context)

        # Verify the structure of the response
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["loaded"])
        self.assertEqual(result["options_count"], 1234)
        self.assertIn("cache_stats", result)
        self.assertEqual(result["cache_stats"]["hits"], 100)
        self.assertEqual(result["cache_stats"]["misses"], 20)
        self.assertAlmostEqual(result["cache_stats"]["hit_ratio"], 0.83)

    def test_search_options_resource(self):
        """Test the home-manager://search/options/{query} resource."""
        # Mock the search_options method
        self.mock_context.search_options.return_value = {
            "count": 2,
            "options": [
                {
                    "name": "programs.git.enable",
                    "type": "boolean",
                    "description": "Whether to enable Git.",
                    "category": "Version Control",
                    "default": "false",
                },
                {
                    "name": "programs.git.userName",
                    "type": "string",
                    "description": "Your Git username.",
                    "category": "Version Control",
                    "default": None,
                },
            ],
        }

        # Call the resource function with our mock context
        result = home_manager_search_options_resource("git", self.mock_context)

        # Verify the structure of the response
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(result["options"]), 2)
        self.assertEqual(result["options"][0]["name"], "programs.git.enable")
        self.assertEqual(result["options"][1]["name"], "programs.git.userName")
        self.assertEqual(result["options"][0]["type"], "boolean")
        self.assertEqual(result["options"][1]["type"], "string")

        # Verify the mock was called correctly
        self.mock_context.search_options.assert_called_once_with("git")

    def test_option_resource_found(self):
        """Test the home-manager://option/{option_name} resource when option is found."""
        # Mock the get_option method
        self.mock_context.get_option.return_value = {
            "name": "programs.git.enable",
            "type": "boolean",
            "description": "Whether to enable Git.",
            "category": "Version Control",
            "default": "false",
            "example": "true",
            "source": "options",
            "found": True,
            "related_options": [
                {
                    "name": "programs.git.userName",
                    "type": "string",
                    "description": "Your Git username.",
                },
            ],
        }

        # Call the resource function with our mock context
        result = home_manager_option_resource("programs.git.enable", self.mock_context)

        # Verify the structure of the response
        self.assertEqual(result["name"], "programs.git.enable")
        self.assertEqual(result["type"], "boolean")
        self.assertEqual(result["description"], "Whether to enable Git.")
        self.assertEqual(result["category"], "Version Control")
        self.assertEqual(result["default"], "false")
        self.assertEqual(result["example"], "true")
        self.assertEqual(result["source"], "options")
        self.assertTrue(result["found"])

        # Verify related options
        self.assertIn("related_options", result)
        self.assertEqual(len(result["related_options"]), 1)
        self.assertEqual(result["related_options"][0]["name"], "programs.git.userName")

    def test_option_resource_not_found(self):
        """Test the home-manager://option/{option_name} resource when option is not found."""
        # Mock the get_option method
        self.mock_context.get_option.return_value = {
            "name": "programs.nonexistent",
            "found": False,
            "error": "Option not found",
        }

        # Call the resource function with our mock context
        result = home_manager_option_resource("programs.nonexistent", self.mock_context)

        # Verify the structure of the response
        self.assertEqual(result["name"], "programs.nonexistent")
        self.assertFalse(result["found"])
        self.assertEqual(result["error"], "Option not found")

    def test_options_stats_resource(self):
        """Test the home-manager://options/stats resource."""
        # Mock the get_stats method
        self.mock_context.get_stats.return_value = {
            "total_options": 1234,
            "total_categories": 42,
            "total_types": 10,
            "by_source": {
                "options": 800,
                "nixos-options": 434,
            },
            "by_category": {
                "Version Control": 50,
                "Web Browsers": 30,
                "Text Editors": 20,
            },
            "by_type": {
                "boolean": 500,
                "string": 400,
                "integer": 150,
                "list": 100,
                "attribute set": 84,
            },
        }

        # Call the resource function with our mock context
        result = home_manager_stats_resource(self.mock_context)

        # Verify the structure of the response
        self.assertEqual(result["total_options"], 1234)
        self.assertEqual(result["total_categories"], 42)
        self.assertEqual(result["total_types"], 10)

        # Verify source distribution
        self.assertIn("by_source", result)
        self.assertEqual(result["by_source"]["options"], 800)
        self.assertEqual(result["by_source"]["nixos-options"], 434)

        # Verify category distribution
        self.assertIn("by_category", result)
        self.assertEqual(result["by_category"]["Version Control"], 50)
        self.assertEqual(result["by_category"]["Web Browsers"], 30)

        # Verify type distribution
        self.assertIn("by_type", result)
        self.assertEqual(result["by_type"]["boolean"], 500)
        self.assertEqual(result["by_type"]["string"], 400)

    def test_options_list_resource(self):
        """Test the home-manager://options/list resource."""
        # Mock the get_options_list method
        self.mock_context.get_options_list.return_value = {
            "options": {
                "programs": {
                    "count": 50,
                    "enable_options": [
                        {"name": "programs.git.enable", "parent": "git", "description": "Enable Git configuration."}
                    ],
                    "types": {"boolean": 20, "string": 15, "attrsOf": 10, "other": 5},
                    "has_children": True,
                },
                "services": {
                    "count": 30,
                    "enable_options": [
                        {
                            "name": "services.syncthing.enable",
                            "parent": "syncthing",
                            "description": "Enable Syncthing service.",
                        }
                    ],
                    "types": {"boolean": 15, "string": 10, "other": 5},
                    "has_children": True,
                },
            },
            "count": 2,
            "found": True,
        }

        # Call the resource function with our mock context
        result = home_manager_options_list_resource(self.mock_context)

        # Verify the structure of the response
        self.assertTrue(result["found"])
        self.assertEqual(result["count"], 2)
        self.assertIn("options", result)
        self.assertIn("programs", result["options"])
        self.assertIn("services", result["options"])
        self.assertEqual(result["options"]["programs"]["count"], 50)
        self.assertEqual(result["options"]["services"]["count"], 30)
        self.assertTrue(result["options"]["programs"]["has_children"])

        # Verify enable options
        self.assertIn("enable_options", result["options"]["programs"])
        self.assertEqual(len(result["options"]["programs"]["enable_options"]), 1)
        self.assertEqual(result["options"]["programs"]["enable_options"][0]["parent"], "git")

        # Verify type distribution
        self.assertIn("types", result["options"]["programs"])
        self.assertEqual(result["options"]["programs"]["types"]["boolean"], 20)
        self.assertEqual(result["options"]["programs"]["types"]["string"], 15)

    def test_options_list_resource_error(self):
        """Test the home-manager://options/list resource when an error occurs."""
        # Mock the get_options_list method to return an error
        self.mock_context.get_options_list.return_value = {"error": "Failed to get options list", "found": False}

        # Call the resource function with our mock context
        result = home_manager_options_list_resource(self.mock_context)

        # Verify the structure of the response
        self.assertFalse(result["found"])
        self.assertEqual(result["error"], "Failed to get options list")

    def test_options_by_prefix_resource_programs(self):
        """Test the home-manager://options/programs resource."""
        # Mock the get_options_by_prefix method
        self.mock_context.get_options_by_prefix.return_value = {
            "prefix": "programs",
            "options": [
                {
                    "name": "programs.git.enable",
                    "type": "boolean",
                    "description": "Whether to enable Git configuration.",
                },
                {"name": "programs.firefox.enable", "type": "boolean", "description": "Whether to enable Firefox."},
            ],
            "count": 2,
            "types": {"boolean": 2},
            "enable_options": [
                {"name": "programs.git.enable", "parent": "git", "description": "Whether to enable Git configuration."},
                {"name": "programs.firefox.enable", "parent": "firefox", "description": "Whether to enable Firefox."},
            ],
            "found": True,
        }

        # Call the resource function with our mock context
        result = home_manager_options_by_prefix_resource("programs", self.mock_context)

        # Verify the structure of the response
        self.assertTrue(result["found"])
        self.assertEqual(result["prefix"], "programs")
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(result["options"]), 2)

        # Verify options structure
        self.assertEqual(result["options"][0]["name"], "programs.git.enable")
        self.assertEqual(result["options"][0]["type"], "boolean")

        # Verify enable options
        self.assertIn("enable_options", result)
        self.assertEqual(len(result["enable_options"]), 2)

        # Verify type distribution
        self.assertIn("types", result)
        self.assertEqual(result["types"]["boolean"], 2)

        # Verify the mock was called correctly
        self.mock_context.get_options_by_prefix.assert_called_once_with("programs")

    def test_options_by_prefix_resource_services(self):
        """Test the home-manager://options/services resource."""
        # Mock the get_options_by_prefix method
        self.mock_context.get_options_by_prefix.return_value = {
            "prefix": "services",
            "options": [
                {
                    "name": "services.syncthing.enable",
                    "type": "boolean",
                    "description": "Whether to enable Syncthing service.",
                }
            ],
            "count": 1,
            "types": {"boolean": 1},
            "enable_options": [
                {
                    "name": "services.syncthing.enable",
                    "parent": "syncthing",
                    "description": "Whether to enable Syncthing service.",
                }
            ],
            "found": True,
        }

        # Call the resource function with our mock context
        result = home_manager_options_by_prefix_resource("services", self.mock_context)

        # Verify the structure of the response
        self.assertTrue(result["found"])
        self.assertEqual(result["prefix"], "services")
        self.assertEqual(result["count"], 1)

        # Verify the mock was called correctly
        self.mock_context.get_options_by_prefix.assert_called_once_with("services")

    def test_options_by_prefix_resource_generic(self):
        """Test the home-manager://options/prefix/{option_prefix} resource for nested paths."""
        # Mock the get_options_by_prefix method
        self.mock_context.get_options_by_prefix.return_value = {
            "prefix": "programs.git",
            "options": [
                {
                    "name": "programs.git.enable",
                    "type": "boolean",
                    "description": "Whether to enable Git configuration.",
                },
                {"name": "programs.git.userName", "type": "string", "description": "The user name to use for Git."},
                {
                    "name": "programs.git.userEmail",
                    "type": "string",
                    "description": "The email address to use for Git.",
                },
            ],
            "count": 3,
            "types": {"boolean": 1, "string": 2},
            "enable_options": [
                {"name": "programs.git.enable", "parent": "git", "description": "Whether to enable Git configuration."}
            ],
            "found": True,
        }

        # Call the resource function with our mock context
        result = home_manager_options_by_prefix_resource("programs.git", self.mock_context)

        # Verify the structure of the response
        self.assertTrue(result["found"])
        self.assertEqual(result["prefix"], "programs.git")
        self.assertEqual(result["count"], 3)
        self.assertEqual(len(result["options"]), 3)

        # Verify options structure
        self.assertEqual(result["options"][0]["name"], "programs.git.enable")
        self.assertEqual(result["options"][0]["type"], "boolean")
        self.assertEqual(result["options"][1]["name"], "programs.git.userName")
        self.assertEqual(result["options"][1]["type"], "string")

        # Verify enable options
        self.assertIn("enable_options", result)
        self.assertEqual(len(result["enable_options"]), 1)
        self.assertEqual(result["enable_options"][0]["parent"], "git")

        # Verify type distribution
        self.assertIn("types", result)
        self.assertEqual(result["types"]["boolean"], 1)
        self.assertEqual(result["types"]["string"], 2)

        # Verify the mock was called correctly
        self.mock_context.get_options_by_prefix.assert_called_once_with("programs.git")

    def test_options_by_prefix_resource_error(self):
        """Test the home-manager://options/prefix/{option_prefix} resource when an error occurs."""
        # Mock the get_options_by_prefix method to return an error
        self.mock_context.get_options_by_prefix.return_value = {
            "error": "No options found with prefix 'invalid.prefix'",
            "found": False,
        }

        # Call the resource function with our mock context
        result = home_manager_options_by_prefix_resource("invalid.prefix", self.mock_context)

        # Verify the structure of the response
        self.assertFalse(result["found"])
        self.assertEqual(result["error"], "No options found with prefix 'invalid.prefix'")

        # Verify the mock was called correctly
        self.mock_context.get_options_by_prefix.assert_called_once_with("invalid.prefix")


if __name__ == "__main__":
    import unittest

    unittest.main()
