"""Test Home Manager resource endpoints."""

import logging
from unittest.mock import patch, MagicMock

# Import base test class
from tests import NixMCPTestBase

# Import the server module
from nixmcp.server import (
    home_manager_status_resource,
    home_manager_search_options_resource,
    home_manager_option_resource,
    home_manager_stats_resource,
    HomeManagerContext,
)

# Disable logging during tests
logging.disable(logging.CRITICAL)


class TestHomeManagerResourceEndpoints(NixMCPTestBase):
    """Test the Home Manager MCP resource endpoints."""

    def setUp(self):
        """Set up the test environment."""
        # Create a mock for the HomeManagerContext
        self.context_patcher = patch('nixmcp.server.home_manager_context')
        self.mock_context = self.context_patcher.start()
        self.addCleanup(self.context_patcher.stop)

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

        # Call the resource function
        result = home_manager_status_resource()

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

        # Call the resource function
        result = home_manager_search_options_resource("git")

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

        # Call the resource function
        result = home_manager_option_resource("programs.git.enable")

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

        # Call the resource function
        result = home_manager_option_resource("programs.nonexistent")

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

        # Call the resource function
        result = home_manager_stats_resource()

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


if __name__ == "__main__":
    import unittest
    unittest.main()