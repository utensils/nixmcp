import logging
import unittest  # Import explicitly for the main block
import pytest
from unittest.mock import Mock

# Mark as unit tests
pytestmark = pytest.mark.unit

# Import base test class
from tests import MCPNixOSTestBase

# Import the resource functions directly from the resources module
from mcp_nixos.resources.home_manager_resources import (
    home_manager_status_resource,
    home_manager_search_options_resource,
    home_manager_option_resource,
    home_manager_stats_resource,
    home_manager_options_list_resource,
    home_manager_options_by_prefix_resource,
)

# Disable logging during tests - Keep this as it's effective for tests
logging.disable(logging.CRITICAL)


class TestHomeManagerResourceEndpoints(MCPNixOSTestBase):
    """Test the Home Manager MCP resource endpoints."""

    def setUp(self):
        """Set up the test environment."""
        # Create a mock for the HomeManagerContext - This remains the same
        self.mock_context = Mock()

    def test_status_resource(self):
        """Test the home-manager://status resource."""
        # Define the expected result directly
        expected_status = {
            "status": "ok",
            "loaded": True,
            "options_count": 1234,
            "cache_stats": {
                "size": 50,
                "max_size": 100,
                "ttl": 86400,
                "hits": 100,
                "misses": 20,
                "hit_ratio": 0.83,
            },
        }
        # Mock the get_status method
        self.mock_context.get_status.return_value = expected_status

        # Call the resource function
        result = home_manager_status_resource(self.mock_context)

        # Verify the mock was called
        self.mock_context.get_status.assert_called_once()

        # Verify result is the same as what was returned by get_status
        self.assertEqual(result, expected_status)

        # The test was failing because home_manager_status_resource should
        # directly pass through the result from context.get_status without
        # modification, and our test was expecting to modify the dictionaries
        # (by popping hit_ratio) which would fail if they were the same object.
        # This simplified implementation properly tests that the resource function
        # correctly returns whatever the context's get_status method returns.

    def test_search_options_resource(self):
        """Test the home-manager://search/options/{query} resource."""
        expected_search_result = {
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
        self.mock_context.search_options.return_value = expected_search_result

        result = home_manager_search_options_resource("git", self.mock_context)

        # --- Optimized Assertion ---
        self.assertEqual(result, expected_search_result)
        # ----------------------------

        self.mock_context.search_options.assert_called_once_with("git")

    def test_option_resource_found(self):
        """Test the home-manager://option/{option_name} resource when option is found."""
        expected_option_found = {
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
        self.mock_context.get_option.return_value = expected_option_found

        result = home_manager_option_resource("programs.git.enable", self.mock_context)

        # --- Optimized Assertion ---
        self.assertEqual(result, expected_option_found)
        # ----------------------------

        self.mock_context.get_option.assert_called_once_with("programs.git.enable")

    def test_option_resource_not_found(self):
        """Test the home-manager://option/{option_name} resource when option is not found."""
        expected_option_not_found = {
            "name": "programs.nonexistent",
            "found": False,
            "error": "Option not found",
        }
        self.mock_context.get_option.return_value = expected_option_not_found

        result = home_manager_option_resource("programs.nonexistent", self.mock_context)

        # --- Optimized Assertion ---
        self.assertEqual(result, expected_option_not_found)
        # ----------------------------

        self.mock_context.get_option.assert_called_once_with("programs.nonexistent")

    def test_options_stats_resource(self):
        """Test the home-manager://options/stats resource."""
        expected_stats = {
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
        self.mock_context.get_stats.return_value = expected_stats

        result = home_manager_stats_resource(self.mock_context)

        # --- Optimized Assertion ---
        self.assertEqual(result, expected_stats)
        # ----------------------------

        self.mock_context.get_stats.assert_called_once()

    def test_options_list_resource(self):
        """Test the home-manager://options/list resource."""
        expected_list_result = {
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
        self.mock_context.get_options_list.return_value = expected_list_result

        result = home_manager_options_list_resource(self.mock_context)

        # --- Optimized Assertion ---
        self.assertEqual(result, expected_list_result)
        # ----------------------------

        self.mock_context.get_options_list.assert_called_once()

    def test_options_list_resource_error(self):
        """Test the home-manager://options/list resource when an error occurs."""
        expected_list_error = {"error": "Failed to get options list", "found": False}
        self.mock_context.get_options_list.return_value = expected_list_error

        result = home_manager_options_list_resource(self.mock_context)

        # --- Optimized Assertion ---
        self.assertEqual(result, expected_list_error)
        # ----------------------------

        self.mock_context.get_options_list.assert_called_once()

    def test_options_by_prefix_resource_programs(self):
        """Test the home-manager://options/programs resource."""
        expected_prefix_programs = {
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
        self.mock_context.get_options_by_prefix.return_value = expected_prefix_programs

        result = home_manager_options_by_prefix_resource("programs", self.mock_context)

        # --- Optimized Assertion ---
        self.assertEqual(result, expected_prefix_programs)
        # ----------------------------

        self.mock_context.get_options_by_prefix.assert_called_once_with("programs")

    def test_options_by_prefix_resource_services(self):
        """Test the home-manager://options/services resource."""
        expected_prefix_services = {
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
        self.mock_context.get_options_by_prefix.return_value = expected_prefix_services

        result = home_manager_options_by_prefix_resource("services", self.mock_context)

        # --- Optimized Assertion ---
        self.assertEqual(result, expected_prefix_services)
        # ----------------------------

        self.mock_context.get_options_by_prefix.assert_called_once_with("services")

    def test_options_by_prefix_resource_generic(self):
        """Test the home-manager://options/prefix/{option_prefix} resource for nested paths."""
        expected_prefix_generic = {
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
        self.mock_context.get_options_by_prefix.return_value = expected_prefix_generic

        result = home_manager_options_by_prefix_resource("programs.git", self.mock_context)

        # --- Optimized Assertion ---
        self.assertEqual(result, expected_prefix_generic)
        # ----------------------------

        self.mock_context.get_options_by_prefix.assert_called_once_with("programs.git")

    def test_options_by_prefix_resource_error(self):
        """Test the home-manager://options/prefix/{option_prefix} resource when an error occurs."""
        expected_prefix_error = {
            "error": "No options found with prefix 'invalid.prefix'",
            "found": False,
        }
        self.mock_context.get_options_by_prefix.return_value = expected_prefix_error

        result = home_manager_options_by_prefix_resource("invalid.prefix", self.mock_context)

        # --- Optimized Assertion ---
        self.assertEqual(result, expected_prefix_error)
        # ----------------------------

        self.mock_context.get_options_by_prefix.assert_called_once_with("invalid.prefix")


# Keep the standard unittest runner block
if __name__ == "__main__":
    unittest.main()
