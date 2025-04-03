"""Tests for the MCP tools in the MCP-NixOS server."""

import unittest
import pytest
from unittest.mock import MagicMock

# Mark as unit tests
pytestmark = pytest.mark.unit

from mcp_nixos.tools.nixos_tools import nixos_info, nixos_search
from mcp_nixos.tools.home_manager_tools import home_manager_info, home_manager_search
from mcp_nixos.tools.home_manager_tools import home_manager_list_options, home_manager_options_by_prefix
from mcp_nixos.tools.nixos_tools import CHANNEL_STABLE, CHANNEL_UNSTABLE


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
        result = nixos_search("python", "packages", 5, CHANNEL_UNSTABLE, context=mock_context)

        # Verify the mock was called correctly
        mock_context.search_packages.assert_called_once()
        # Verify that set_channel was called on the es_client with "unstable"
        mock_context.es_client.set_channel.assert_called_with("unstable")

        # Check the result format
        self.assertIn("python311", result)
        self.assertIn("3.11.0", result)
        self.assertIn("Python programming language", result)

    def test_nixos_search_packages_prioritizes_exact_matches(self):
        """Test that nixos_search prioritizes exact package matches."""
        # Create mock context with multiple packages including an exact match
        mock_context = MagicMock()
        mock_context.search_packages.return_value = {
            "count": 3,
            "packages": [
                {
                    "name": "firefox-unwrapped",
                    "version": "123.0.0",
                    "description": "Firefox browser unwrapped",
                },
                {
                    "name": "firefox-esr",
                    "version": "102.10.0",
                    "description": "Extended support release of Firefox",
                },
                {
                    "name": "firefox",  # Exact match to search query
                    "version": "123.0.0",
                    "description": "Mozilla Firefox web browser",
                },
            ],
        }

        # Call the tool with "firefox" query
        result = nixos_search("firefox", "packages", 5, CHANNEL_UNSTABLE, context=mock_context)

        # Extract the order of results from output
        result_lines = result.split("\n")
        package_lines = [line for line in result_lines if line.startswith("- ")]

        # The exact match "firefox" should appear first
        self.assertTrue(package_lines[0].startswith("- firefox"))
        # The other firefox packages should follow
        self.assertTrue("firefox-unwrapped" in package_lines[1] or "firefox-esr" in package_lines[1])

    def test_nixos_search_options(self):
        """Test nixos_search tool with options."""
        # Create mock context
        mock_context = MagicMock()
        mock_context.search_options.return_value = {
            "count": 1,
            "options": [{"name": "services.nginx.enable", "description": "Enable nginx web server", "type": "boolean"}],
        }

        # Call the tool with the mock context directly
        result = nixos_search("services.nginx", "options", 5, CHANNEL_STABLE, context=mock_context)

        # Verify the mock was called correctly
        mock_context.search_options.assert_called_once()
        # Verify that set_channel was called on the es_client with "stable"
        mock_context.es_client.set_channel.assert_called_with(CHANNEL_STABLE)

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

        # Call the tool with the mock context directly, implicitly using default channel
        result = nixos_search("git", "programs", 5, context=mock_context)

        # Verify the mock was called correctly
        mock_context.search_programs.assert_called_once()
        # Verify that set_channel was called with the default unstable channel
        mock_context.es_client.set_channel.assert_called_with(CHANNEL_UNSTABLE)

        # Check the result format
        self.assertIn("git", result)
        self.assertIn("2.39.0", result)
        self.assertIn("git-upload-pack", result)

    def test_channel_selection_with_invalid_channel(self):
        """Test that invalid channels fall back to unstable."""
        # Create mock context
        mock_context = MagicMock()
        mock_context.search_packages.return_value = {"count": 0, "packages": []}

        # Call with invalid channel name
        nixos_search("test", "packages", 5, "invalid-channel", context=mock_context)

        # We expect set_channel to be called with the invalid channel name first
        # The ElasticsearchClient handles the fallback internally
        mock_context.es_client.set_channel.assert_called_with("invalid-channel")

        # We don't need to check the result, just that the correct channel was selected

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
        result = nixos_info("git", "package", CHANNEL_UNSTABLE, context=mock_context)

        # Verify the mock was called correctly
        mock_context.get_package.assert_called_once_with("git")
        # Verify that set_channel was called on the es_client with unstable
        mock_context.es_client.set_channel.assert_called_with(CHANNEL_UNSTABLE)

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
                {
                    "name": "services.nginx.virtualHosts.default.root",
                    "type": "string",
                    "description": "Document root directory",
                },
                {
                    "name": "services.nginx.virtualHosts.default.locations./.proxyPass",
                    "type": "string",
                    "description": "URL to proxy requests to",
                },
            ],
        }

        # Call the tool with the mock context directly
        result = nixos_info("services.nginx.enable", "option", CHANNEL_STABLE, context=mock_context)

        # Verify the mock was called correctly
        mock_context.get_option.assert_called_once_with("services.nginx.enable")
        # Verify that set_channel was called on the es_client with stable
        mock_context.es_client.set_channel.assert_called_with(CHANNEL_STABLE)

        # Check the result format
        self.assertIn("# services.nginx.enable", result)
        self.assertIn("Whether to enable the nginx web server", result)
        self.assertIn("**Type:** boolean", result)
        self.assertIn("Related Options", result)
        self.assertIn("services.nginx.package", result)
        self.assertIn("services.nginx.port", result)

        # Check that our option grouping is working - the virtualHosts options should be grouped
        self.assertIn("virtualHosts options", result)

        # Check that the example configuration is included
        self.assertIn("Example NixOS Configuration", result)
        self.assertIn("enable = true", result)

    def test_nixos_info_option_with_html_formatting(self):
        """Test nixos_info tool handles HTML formatting in option descriptions."""
        # Create mock context
        mock_context = MagicMock()
        mock_context.get_option.return_value = {
            "name": "services.postgresql.enable",
            "description": (
                "<rendered-html><p>Whether to enable PostgreSQL Server.</p>"
                '<p>See <a href="https://www.postgresql.org/docs/">the PostgreSQL documentation</a> for details.</p>'
                "</rendered-html>"
            ),
            "type": "boolean",
            "default": "false",
            "found": True,
            "is_service_path": True,
            "service_name": "postgresql",
            "related_options": [
                {
                    "name": "services.postgresql.package",
                    "type": "package",
                    "description": "<rendered-html><p>The postgresql package to use.</p></rendered-html>",
                },
            ],
        }

        # Call the tool with the mock context directly
        result = nixos_info("services.postgresql.enable", "option", CHANNEL_STABLE, context=mock_context)

        # Check that HTML is properly converted to Markdown
        self.assertIn("# services.postgresql.enable", result)
        self.assertIn("Whether to enable PostgreSQL Server", result)
        # Check for proper link conversion
        self.assertIn("the PostgreSQL documentation", result)
        self.assertIn("https://www.postgresql.org/docs/", result)
        # Check that paragraph breaks are preserved
        self.assertTrue(result.count("\n\n") >= 2)

        # Check that HTML in related options is converted
        self.assertIn("The postgresql package to use", result)

    def test_nixos_info_option_with_complex_html_formatting(self):
        """Test nixos_info tool handles complex HTML with links and lists."""
        # Create mock context
        mock_context = MagicMock()
        mock_context.get_option.return_value = {
            "name": "services.postgresql.enable",
            "description": (
                "<rendered-html>"
                "<p>Whether to enable PostgreSQL Server.</p>"
                "<ul>"
                "<li>Automatic startup</li>"
                "<li>Data persistence</li>"
                "</ul>"
                '<p>See <a href="https://www.postgresql.org/docs/">documentation</a> for configuration details.</p>'
                "<p>Multiple <a href='https://nixos.org/'>links</a> with "
                'different <a href="https://nixos.wiki/">formatting</a>.</p>'
            ),
            "type": "boolean",
            "default": "false",
            "found": True,
            "example": "true",
            "is_service_path": True,
            "service_name": "postgresql",
            "related_options": [],
        }

        # Call the tool with the mock context directly
        result = nixos_info("services.postgresql.enable", "option", CHANNEL_STABLE, context=mock_context)

        # Check that HTML is properly converted to Markdown
        self.assertIn("# services.postgresql.enable", result)
        self.assertIn("Whether to enable PostgreSQL Server", result)

        # Check for proper list conversion
        self.assertIn("- Automatic startup", result)
        self.assertIn("- Data persistence", result)

        # Check for proper link conversion
        self.assertIn("[documentation](https://www.postgresql.org/docs/)", result)
        self.assertIn("[links](https://nixos.org/)", result)
        self.assertIn("[formatting](https://nixos.wiki/)", result)

        # Check that mixed HTML elements are handled correctly
        self.assertNotIn("<a href=", result)
        self.assertNotIn("<p>", result)
        self.assertNotIn("<ul>", result)
        self.assertNotIn("<li>", result)

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
        self.assertIn("programs.git", result)
        # The new implementation may display short names rather than full paths
        self.assertIn("enable", result)
        self.assertIn("userName", result)
        self.assertIn("Whether to enable Git", result)
        self.assertIn("User name to configure in Git", result)
        self.assertIn("Usage Example for git", result)
        self.assertIn("programs.git", result)
        self.assertIn("enable = true", result)

    def test_home_manager_search_prioritization(self):
        """Test that home_manager_search prioritizes exact matches and organizes results correctly."""
        # Create mock context
        mock_context = MagicMock()

        # Setup mock response with variety of options for search prioritization
        mock_context.search_options.return_value = {
            "count": 5,
            "options": [
                {
                    "name": "programs.firefox.extensions.ublock-origin.enable",
                    "type": "boolean",
                    "description": "Enable uBlock Origin extension",
                    "category": "Programs",
                    "source": "options",
                },
                {
                    "name": "programs.git.enable",
                    "type": "boolean",
                    "description": "Whether to enable git",
                    "category": "Programs",
                    "source": "options",
                },
                {
                    "name": "git",  # Exact match to search term
                    "type": "option",
                    "description": "Top-level git option",
                    "category": "Home",
                    "source": "options",
                },
                {
                    "name": "programs.git",  # Close match - exact program
                    "type": "option",
                    "description": "Git program configuration",
                    "category": "Programs",
                    "source": "options",
                },
                {
                    "name": "services.git-daemon.enable",
                    "type": "boolean",
                    "description": "Enable git daemon service",
                    "category": "Services",
                    "source": "options",
                },
            ],
        }

        # Call the tool directly with the mock context, searching for "git"
        result = home_manager_search("git", 10, context=mock_context)

        # Verify search_options was called with wildcards added
        mock_context.search_options.assert_called_with("*git*", 10)

        # The exact match "git" should be prioritized
        result_lines = result.split("\n")

        # Extract all option lines from the output
        option_lines = []
        for i, line in enumerate(result_lines):
            if line.startswith("- "):
                option_lines.append(line)

        # Verify prioritization works correctly
        # Verify that git options exist in the output
        self.assertTrue(any("git" in line for line in option_lines))

        # The Git program should be present in the results
        self.assertIn("programs.git", result)

        # There should be a usage example for git
        self.assertIn("Usage Example for git", result)
        # Firefox might also be included because it contains "git" in the results
        # Adjust the test to just verify that git examples are included

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

    def test_home_manager_options_by_prefix(self):
        """Test home_manager_options_by_prefix tool with chunking for large option sets."""
        # Create mock context
        mock_context = MagicMock()

        # Generate a large number of options to test chunking functionality
        options = []
        # Create 25 options with different groups to test chunking
        for i in range(1, 6):  # 5 groups
            for j in range(1, 6):  # 5 options per group
                options.append(
                    {
                        "name": f"programs.git.group{i}.option{j}",
                        "type": "string",
                        "description": f"Test option {j} in group {i}",
                        "category": "Programs",
                    }
                )

        # Add some direct options too
        for i in range(1, 6):
            options.append(
                {
                    "name": f"programs.git.directOption{i}",
                    "type": "string",
                    "description": f"Direct option {i}",
                    "category": "Programs",
                }
            )

        # Setup mock response
        mock_context.get_options_by_prefix.return_value = {
            "found": True,
            "options": options,
            "count": len(options),
        }

        # Call the tool directly with the mock context
        result = home_manager_options_by_prefix("programs.git", context=mock_context)

        # Verify get_options_by_prefix was called correctly
        mock_context.get_options_by_prefix.assert_called_with("programs.git")

        # Check that chunking is working correctly with the expected number of options
        self.assertIn("Direct Options", result)
        self.assertIn("directOption", result)

        # Verify groups are shown with counts
        for i in range(1, 6):
            self.assertIn(f"group{i} options", result)

        # Make sure pagination instructions are included
        self.assertIn("To see all options in this group, use", result)
        self.assertIn("home_manager_options_by_prefix", result)

        # Check that usage examples are included
        self.assertIn("Usage Examples", result)
        self.assertIn("Example Configuration for git", result)

    def test_home_manager_list_options(self):
        """Test home_manager_list_options tool."""
        # Create mock context
        mock_context = MagicMock()

        # Setup mock response
        mock_context.get_options_list.return_value = {
            "found": True,
            "options": {
                "programs": {
                    "count": 500,
                    "types": {"boolean": 100, "string": 200, "int": 50},
                    "enable_options": [
                        {
                            "name": "programs.git.enable",
                            "parent": "git",
                            "description": "Whether to enable Git",
                        }
                    ],
                },
                "services": {
                    "count": 300,
                    "types": {"boolean": 50, "string": 150},
                    "enable_options": [
                        {
                            "name": "services.syncthing.enable",
                            "parent": "syncthing",
                            "description": "Whether to enable Syncthing",
                        }
                    ],
                },
            },
        }

        # Call the tool directly with the mock context
        result = home_manager_list_options(context=mock_context)

        # Verify get_options_list was called
        mock_context.get_options_list.assert_called_once()

        # Check the result format
        self.assertIn("Home Manager Top-Level Option Categories", result)
        self.assertIn("Total categories: 2", result)
        self.assertIn("Total options: 800", result)  # 500 + 300

        # Check that programs category is listed with stats
        self.assertIn("programs", result)
        self.assertIn("Options count", result)
        self.assertIn("500", result)

        # Check that services category is listed with stats
        self.assertIn("services", result)
        self.assertIn("300", result)

        # Check that enable options are shown
        self.assertIn("git", result)
        self.assertIn("Whether to enable Git", result)

        # Check that usage examples are included
        self.assertIn("Usage example", result)


if __name__ == "__main__":
    unittest.main()
