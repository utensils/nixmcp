"""Test Home Manager hierarchical tools and resources."""

import logging
import pytest
from unittest.mock import Mock

# Mark as unit tests
pytestmark = pytest.mark.unit

# Import base test class
from tests import MCPNixOSTestBase

# Import the tool functions directly from the tools module
from mcp_nixos.tools.home_manager_tools import (
    home_manager_list_options,
    home_manager_options_by_prefix,
)

# Disable logging during tests
logging.disable(logging.CRITICAL)


class TestHomeManagerHierarchy(MCPNixOSTestBase):
    """Test the Home Manager hierarchical navigation tools."""

    def setUp(self):
        """Set up the test environment."""
        # Create a mock for the HomeManagerContext
        self.mock_context = Mock()

    def test_home_manager_list_options(self):
        """Test the home_manager_list_options tool."""
        # Mock the get_options_list method
        self.mock_context.get_options_list.return_value = {
            "options": {
                "programs": {
                    "count": 50,
                    "enable_options": [
                        {"name": "programs.git.enable", "parent": "git", "description": "Enable Git configuration."},
                        {"name": "programs.firefox.enable", "parent": "firefox", "description": "Enable Firefox."},
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
                "xdg": {
                    "count": 15,
                    "enable_options": [],
                    "types": {"boolean": 5, "string": 5, "path": 5},
                    "has_children": True,
                },
            },
            "count": 3,
            "found": True,
        }

        # Call the tool function with our mock context
        result = home_manager_list_options(context=self.mock_context)

        # Verify the mock was called correctly
        self.mock_context.get_options_list.assert_called_once()

        # Verify the output contains key information
        self.assertIn("Home Manager Top-Level Option Categories", result)
        self.assertIn("Total categories: 3", result)
        self.assertIn("Total options: 95", result)
        self.assertIn("programs", result)
        self.assertIn("services", result)
        self.assertIn("xdg", result)
        self.assertIn("options count**: 50", result.lower())
        self.assertIn("boolean: 20", result.lower())
        self.assertIn("git", result.lower())
        self.assertIn("firefox", result.lower())
        self.assertIn("syncthing", result.lower())
        self.assertIn("home_manager_options_by_prefix", result)

    def test_home_manager_list_options_error(self):
        """Test the home_manager_list_options tool when an error occurs."""
        # Mock the get_options_list method to return an error
        self.mock_context.get_options_list.return_value = {"error": "Failed to get options list", "found": False}

        # Call the tool function with our mock context
        result = home_manager_list_options(context=self.mock_context)

        # Verify the output contains the error message
        self.assertIn("Error:", result)
        self.assertIn("Failed to get options list", result)

    def test_home_manager_options_by_prefix_top_level(self):
        """Test the home_manager_options_by_prefix tool with a top-level prefix."""
        # Mock the get_options_by_prefix method
        self.mock_context.get_options_by_prefix.return_value = {
            "prefix": "programs",
            "options": [
                {"name": "programs.git.enable", "type": "boolean", "description": "Enable Git."},
                {"name": "programs.vim.enable", "type": "boolean", "description": "Enable Vim."},
                {"name": "programs.firefox.enable", "type": "boolean", "description": "Enable Firefox."},
            ],
            "count": 3,
            "types": {"boolean": 3},
            "enable_options": [
                {"name": "programs.git.enable", "parent": "git", "description": "Enable Git."},
                {"name": "programs.vim.enable", "parent": "vim", "description": "Enable Vim."},
                {"name": "programs.firefox.enable", "parent": "firefox", "description": "Enable Firefox."},
            ],
            "found": True,
        }

        # Call the tool function with our mock context
        result = home_manager_options_by_prefix("programs", context=self.mock_context)

        # Verify the mock was called correctly
        self.mock_context.get_options_by_prefix.assert_called_once_with("programs")

        # Verify the output contains key information
        self.assertIn("Home Manager Options: programs", result)
        self.assertIn("Found 3 options", result)
        self.assertIn("Enable Options", result)
        self.assertIn("git", result)
        self.assertIn("vim", result)
        self.assertIn("firefox", result)
        self.assertIn("Option Groups", result)

    def test_home_manager_options_by_prefix_nested(self):
        """Test the home_manager_options_by_prefix tool with a nested prefix."""
        # Mock the get_options_by_prefix method
        self.mock_context.get_options_by_prefix.return_value = {
            "prefix": "programs.git",
            "options": [
                {"name": "programs.git.enable", "type": "boolean", "description": "Enable Git."},
                {"name": "programs.git.userName", "type": "string", "description": "Git username."},
                {"name": "programs.git.userEmail", "type": "string", "description": "Git email."},
                {"name": "programs.git.signing.key", "type": "string", "description": "Signing key."},
                {"name": "programs.git.signing.signByDefault", "type": "boolean", "description": "Sign by default."},
            ],
            "count": 5,
            "types": {"boolean": 2, "string": 3},
            "enable_options": [{"name": "programs.git.enable", "parent": "git", "description": "Enable Git."}],
            "found": True,
        }

        # Call the tool function with our mock context
        result = home_manager_options_by_prefix("programs.git", context=self.mock_context)

        # Verify the mock was called correctly
        self.mock_context.get_options_by_prefix.assert_called_once_with("programs.git")

        # Verify the output contains key information
        self.assertIn("Home Manager Options: programs.git", result)
        self.assertIn("Found 5 options", result)
        self.assertIn("Direct Options", result)
        self.assertIn("signing", result)
        self.assertIn("enable", result)
        self.assertIn("userName", result)
        self.assertIn("userEmail", result)
        self.assertIn("Example Configuration for git", result)

    def test_home_manager_options_by_prefix_error(self):
        """Test the home_manager_options_by_prefix tool when an error occurs."""
        # Mock the get_options_by_prefix method to return an error
        self.mock_context.get_options_by_prefix.return_value = {
            "error": "No options found with prefix 'invalid.prefix'",
            "found": False,
        }

        # Call the tool function with our mock context
        result = home_manager_options_by_prefix("invalid.prefix", context=self.mock_context)

        # Verify the output contains the error message
        self.assertIn("Error:", result)
        self.assertIn("No options found with prefix 'invalid.prefix'", result)


if __name__ == "__main__":
    import unittest

    unittest.main()
