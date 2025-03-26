"""Tests for the MCP tools in the NixMCP server."""

import unittest
from unittest.mock import MagicMock
from nixmcp.server import (
    nixos_search,
    nixos_info,
    home_manager_search,
    home_manager_info,
)


class TestNixOSTools(unittest.TestCase):
    """Test the NixOS MCP tools."""

    def test_nixos_search_packages(self):
        """Test nixos_search tool with packages."""
        # Create mock context
        mock_context = MagicMock()
        mock_context.search_packages.return_value = {
            "count": 1,
            "packages": [
                {
                    "name": "python311",
                    "version": "3.11.0",
                    "description": "Python programming language",
                    "programs": ["python3", "python3.11"],
                }
            ],
        }

        # Call the tool with the mock context directly
        result = nixos_search("python", "packages", 5, "unstable", context=mock_context)

        # Verify the mock was called correctly
        mock_context.search_packages.assert_called_once()

        # Check the result format
        self.assertIn("python311", result)
        self.assertIn("3.11.0", result)
        self.assertIn("Python programming language", result)

    def test_nixos_search_options(self):
        """Test nixos_search tool with options."""
        # Create mock context
        mock_context = MagicMock()
        mock_context.search_options.return_value = {
            "count": 1,
            "options": [{"name": "services.nginx.enable", "description": "Enable nginx web server", "type": "boolean"}],
        }

        # Call the tool with the mock context directly
        result = nixos_search("services.nginx", "options", 5, "24.11", context=mock_context)

        # Verify the mock was called correctly
        mock_context.search_options.assert_called_once()

        # Check the result format
        self.assertIn("services.nginx.enable", result)
        self.assertIn("Enable nginx web server", result)
        self.assertIn("boolean", result)

    def test_nixos_search_programs(self):
        """Test nixos_search tool with programs."""
        # Create mock context
        mock_context = MagicMock()
        mock_context.search_programs.return_value = {
            "count": 1,
            "packages": [
                {
                    "name": "git",
                    "version": "2.39.0",
                    "description": "Distributed version control system",
                    "programs": ["git", "git-upload-pack"],
                }
            ],
        }

        # Call the tool with the mock context directly
        result = nixos_search("git", "programs", 5, context=mock_context)

        # Verify the mock was called correctly
        mock_context.search_programs.assert_called_once()

        # Check the result format
        self.assertIn("git", result)
        self.assertIn("2.39.0", result)
        self.assertIn("git-upload-pack", result)

    def test_nixos_search_service_not_found(self):
        """Test nixos_search tool with a service path that returns no results."""
        # Create mock context
        mock_context = MagicMock()
        mock_context.search_options.return_value = {"count": 0, "options": []}

        # Call the tool with the mock context directly
        result = nixos_search("services.nonexistent", "options", 5, context=mock_context)

        # Verify the mock was called correctly
        mock_context.search_options.assert_called_once()

        # Check that suggestions are provided for the service
        self.assertIn("No options found", result)
        self.assertIn("services.nonexistent.enable", result)
        self.assertIn("services.nonexistent.package", result)

    def test_nixos_info_package(self):
        """Test nixos_info tool with a package."""
        # Create mock context
        mock_context = MagicMock()
        mock_context.get_package.return_value = {
            "name": "git",
            "version": "2.39.0",
            "description": "Distributed version control system",
            "longDescription": "Git is a fast, scalable, distributed revision control system.",
            "homepage": "https://git-scm.com/",
            "license": "MIT",
            "programs": ["git", "git-upload-pack", "git-receive-pack"],
            "found": True,
        }

        # Call the tool with the mock context directly
        result = nixos_info("git", "package", "unstable", context=mock_context)

        # Verify the mock was called correctly
        mock_context.get_package.assert_called_once_with("git")

        # Check the result format
        self.assertIn("# git", result)
        self.assertIn("**Version:** 2.39.0", result)
        self.assertIn("Distributed version control system", result)
        self.assertIn("Git is a fast", result)
        self.assertIn("https://git-scm.com/", result)
        self.assertIn("MIT", result)
        self.assertIn("git-upload-pack", result)

    def test_nixos_info_option(self):
        """Test nixos_info tool with an option."""
        # Create mock context
        mock_context = MagicMock()
        mock_context.get_option.return_value = {
            "name": "services.nginx.enable",
            "description": "Whether to enable the nginx web server.",
            "type": "boolean",
            "default": "false",
            "found": True,
            "is_service_path": True,
            "service_name": "nginx",
            "related_options": [
                {"name": "services.nginx.package", "type": "package", "description": "Nginx package to use"},
                {"name": "services.nginx.port", "type": "int", "description": "Port to bind on"},
            ],
        }

        # Call the tool with the mock context directly
        result = nixos_info("services.nginx.enable", "option", "24.11", context=mock_context)

        # Verify the mock was called correctly
        mock_context.get_option.assert_called_once_with("services.nginx.enable")

        # Check the result format
        self.assertIn("# services.nginx.enable", result)
        self.assertIn("Whether to enable the nginx web server", result)
        self.assertIn("**Type:** boolean", result)
        self.assertIn("Related Options", result)
        self.assertIn("services.nginx.package", result)
        self.assertIn("services.nginx.port", result)
        self.assertIn("Example NixOS Configuration", result)
        self.assertIn("enable = true", result)

    def test_nixos_info_option_not_found(self):
        """Test nixos_info tool with an option that doesn't exist."""
        # Create mock context
        mock_context = MagicMock()
        mock_context.get_option.return_value = {
            "name": "services.nonexistent.option",
            "error": "Option not found",
            "found": False,
            "is_service_path": True,
            "service_name": "nonexistent",
        }

        # Call the tool with the mock context directly
        result = nixos_info("services.nonexistent.option", "option", context=mock_context)

        # Verify the mock was called correctly
        mock_context.get_option.assert_called_once_with("services.nonexistent.option")

        # Check the result includes helpful suggestions
        self.assertIn("Option 'services.nonexistent.option' not found", result)
        self.assertIn("Common Options for Services", result)
        self.assertIn("services.nonexistent.enable", result)
        self.assertIn("Example NixOS Configuration", result)


class TestHomeManagerTools(unittest.TestCase):
    """Test the Home Manager MCP tools."""

    def test_home_manager_search(self):
        """Test home_manager_search tool."""
        # Create mock context
        mock_context = MagicMock()

        # Setup mock response
        mock_context.search_options.return_value = {
            "count": 2,
            "options": [
                {
                    "name": "programs.git.enable",
                    "type": "boolean",
                    "description": "Whether to enable Git.",
                    "category": "Programs",
                    "source": "options",
                },
                {
                    "name": "programs.git.userName",
                    "type": "string",
                    "description": "User name to configure in Git.",
                    "category": "Programs",
                    "source": "options",
                },
            ],
        }

        # Call the tool directly with the mock context
        result = home_manager_search("programs.git", 5, context=mock_context)

        # Verify search_options was called with wildcards added
        mock_context.search_options.assert_called_with("*programs.git*", 5)

        # Check the result format
        self.assertIn("Found 2 Home Manager options", result)
        self.assertIn("## Programs", result)
        self.assertIn("programs.git.enable", result)
        self.assertIn("programs.git.userName", result)
        self.assertIn("Whether to enable Git", result)
        self.assertIn("User name to configure in Git", result)
        self.assertIn("## Usage Example for git", result)
        self.assertIn("programs.git = {", result)
        self.assertIn("enable = true", result)

    def test_home_manager_search_empty_results(self):
        """Test home_manager_search tool with no results."""
        # Create mock context
        mock_context = MagicMock()

        # Setup mock for search_options with empty results
        mock_context.search_options.return_value = {"count": 0, "options": []}

        # Call the tool directly with the mock context
        result = home_manager_search("nonexistent_option_xyz", 5, context=mock_context)

        # Verify search_options was called with wildcards added
        mock_context.search_options.assert_called_with("*nonexistent_option_xyz*", 5)

        # Check the result format contains the "not found" message
        self.assertIn("No Home Manager options found", result)

    def test_home_manager_info(self):
        """Test home_manager_info tool."""
        # Create mock context
        mock_context = MagicMock()

        # Setup mock response
        mock_context.get_option.return_value = {
            "name": "programs.git.userName",
            "type": "string",
            "description": "User name to configure in Git.",
            "default": "null",
            "example": '"John Doe"',
            "category": "Programs",
            "source": "options",
            "found": True,
            "related_options": [
                {"name": "programs.git.enable", "type": "boolean", "description": "Whether to enable Git."},
                {
                    "name": "programs.git.userEmail",
                    "type": "string",
                    "description": "Email address to configure in Git.",
                },
            ],
        }

        # Call the tool directly with the mock context
        result = home_manager_info("programs.git.userName", context=mock_context)

        # Verify get_option was called with the correct option name
        mock_context.get_option.assert_called_with("programs.git.userName")

        # Check the result format
        self.assertIn("# programs.git.userName", result)
        self.assertIn("**Description:** User name to configure in Git", result)
        self.assertIn("**Type:** string", result)
        self.assertIn("**Default:** null", result)
        self.assertIn("**Example:**", result)
        self.assertIn('"John Doe"', result)
        self.assertIn("## Related Options", result)
        self.assertIn("programs.git.enable", result)
        self.assertIn("programs.git.userEmail", result)
        self.assertIn("## Example Home Manager Configuration", result)
        self.assertIn("programs.git = {", result)
        self.assertIn('userName = "value"', result)

    def test_home_manager_info_not_found(self):
        """Test home_manager_info tool with option not found."""
        # Create mock context
        mock_context = MagicMock()

        # Setup mock response
        mock_context.get_option.return_value = {
            "name": "programs.git.fullnam",  # Typo in name
            "error": "Option not found. Did you mean 'programs.git.userName'?",
            "found": False,
            "suggestions": ["programs.git.userName", "programs.git.userEmail"],
        }

        # Call the tool directly with the mock context
        result = home_manager_info("programs.git.fullnam", context=mock_context)

        # Verify get_option was called with the incorrect name
        mock_context.get_option.assert_called_with("programs.git.fullnam")

        # Verify the not found message and suggestions
        self.assertIn("# Option 'programs.git.fullnam' not found", result)
        self.assertIn("Did you mean one of these options?", result)
        self.assertIn("- programs.git.userName", result)
        self.assertIn("- programs.git.userEmail", result)
        self.assertIn("Try searching for all options under this path", result)
        self.assertIn('`home_manager_search(query="programs.git")`', result)


if __name__ == "__main__":
    unittest.main()
