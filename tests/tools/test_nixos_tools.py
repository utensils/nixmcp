"""
Tests for the NixOS tools module.
"""

import unittest
import importlib
from unittest.mock import patch, MagicMock, call

# Import the module to test
from mcp_nixos.tools.nixos_tools import (
    nixos_search,
    nixos_info,
    nixos_stats,
    check_request_ready,
    register_nixos_tools,
    _setup_context_and_channel,
    _format_search_results,
    _format_package_info,
    _format_license,
    _format_maintainers,
    _create_github_link,
    _simple_html_to_markdown,
    _get_service_suggestion,
    _format_option_info,
)


class TestNixOSTools(unittest.TestCase):
    """Test the NixOS tools functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock context
        self.mock_context = MagicMock()
        self.mock_es_client = MagicMock()
        self.mock_context.es_client = self.mock_es_client

        # Set up mock search results
        self.mock_es_client.search_packages.return_value = {
            "packages": [
                {
                    "name": "git",
                    "version": "2.39.2",
                    "description": "Distributed version control system",
                }
            ]
        }
        self.mock_es_client.search_options.return_value = {
            "options": [
                {
                    "name": "services.nginx",
                    "description": "Nginx web server configuration",
                    "type": "attribute set",
                }
            ]
        }
        self.mock_es_client.search_programs.return_value = {
            "packages": [
                {
                    "name": "git",
                    "version": "2.39.2",
                    "description": "Distributed version control system",
                    "programs": ["git", "git-remote-http"],
                }
            ]
        }

        # Set up mock info results
        self.mock_es_client.get_package_info.return_value = {
            "name": "git",
            "version": "2.39.2",
            "description": "Distributed version control system",
            "license": {"fullName": "GPL-2.0-only"},
            "maintainers": [{"name": "Alice", "email": "alice@example.com"}],
            "position": "pkgs/applications/version-management/git/default.nix:1",
            "homepage": "https://git-scm.com/",
        }
        self.mock_es_client.get_option_info.return_value = {
            "name": "services.nginx",
            "description": "Nginx web server configuration",
            "type": "attribute set",
            "default": {},
            "example": {"enable": True},
            "declared_by": ["nixos/modules/services/web-servers/nginx.nix"],
        }

        # Set up mock stats results
        self.mock_es_client.get_package_stats.return_value = {"total": 80000}
        self.mock_es_client.count_options.return_value = 10000

    def test_setup_context_and_channel(self):
        """Test _setup_context_and_channel function."""
        # Test with provided contex
        result = _setup_context_and_channel(self.mock_context, "unstable")
        self.assertEqual(result, self.mock_context)
        self.mock_es_client.set_channel.assert_called_once_with("unstable")

        # Test with None context and successful dynamic import
        with patch("importlib.import_module") as mock_importlib:
            mock_server = MagicMock()
            mock_server.get_nixos_context.return_value = self.mock_context
            mock_importlib.return_value = mock_server

            # Reset the mock
            self.mock_es_client.set_channel.reset_mock()

            # Call the function
            result = _setup_context_and_channel(None, "unstable")

            # Verify importlib.import_module was called correctly
            mock_importlib.assert_called_with("mcp_nixos.server")
            self.assertEqual(result, self.mock_context)
            self.mock_es_client.set_channel.assert_called_once_with("unstable")

        # Test with None context and failed dynamic impor
        with patch("importlib.import_module") as mock_importlib:
            mock_importlib.side_effect = ImportError("Test error")

            # Call the function
            result = _setup_context_and_channel(None, "unstable")

            # Verify result is None
            self.assertIsNone(result)

        # Test with context missing es_clien
        mock_context_no_client = MagicMock(spec=[])
        result = _setup_context_and_channel(mock_context_no_client, "unstable")
        self.assertEqual(result, mock_context_no_client)

    def test_format_search_results_packages(self):
        """Test _format_search_results for packages."""
        results = {
            "packages": [
                {
                    "name": "git",
                    "version": "2.39.2",
                    "description": "Distributed version control system",
                },
                {
                    "name": "gitAndTools.gitFull",
                    "version": "2.39.2",
                    "description": "Git with all features",
                },
            ]
        }

        # Test with exact match
        result = _format_search_results(results, "git", "packages")
        self.assertIn("Found 2 packages matching", result)
        self.assertIn("git (2.39.2)", result)
        self.assertIn("Distributed version control system", result)

        # Test with no results
        result = _format_search_results({"packages": []}, "nonexistent", "packages")
        self.assertIn("No packages found matching", result)

    def test_format_search_results_options(self):
        """Test _format_search_results for options."""
        results = {
            "options": [
                {
                    "name": "services.nginx",
                    "description": "Nginx web server configuration",
                    "type": "attribute set",
                },
            ]
        }

        # Test with regular option
        result = _format_search_results(results, "nginx", "options")
        self.assertIn("Found 1 options matching 'nginx'", result)
        self.assertIn("services.nginx", result)
        self.assertIn("Type: attribute set", result)

        # Test with service option
        result = _format_search_results(results, "services.nginx", "options")
        self.assertIn("Found 1 options for 'services.nginx'", result)

        # Test with no results
        result = _format_search_results({"options": []}, "nonexistent", "options")
        self.assertIn("No options found matching 'nonexistent'", result)

    def test_format_search_results_programs(self):
        """Test _format_search_results for programs."""
        results = {
            "packages": [
                {
                    "name": "git",
                    "version": "2.39.2",
                    "description": "Distributed version control system",
                    "programs": ["git", "git-remote-http"],
                },
            ]
        }

        # Test with programs
        result = _format_search_results(results, "git", "programs")
        self.assertIn("Found 1 programs matching 'git'", result)
        self.assertIn("git (2.39.2)", result)
        self.assertIn("Programs: git, git-remote-http", result)

        # Test with no results
        result = _format_search_results({"packages": []}, "nonexistent", "programs")
        self.assertIn("No programs found matching 'nonexistent'", result)

    def test_format_package_info(self):
        """Test _format_package_info function."""
        info = {
            "name": "git",
            "version": "2.39.2",
            "description": "Distributed version control system",
            "license": {"fullName": "GPL-2.0-only"},
            "maintainers": [{"name": "Alice", "email": "alice@example.com"}],
            "position": "pkgs/applications/version-management/git/default.nix:1",
            "homepage": "https://git-scm.com/",
            "outputs": ["out", "doc"],
            "system": "x86_64-linux",
        }

        result = _format_package_info(info)
        self.assertIn("# git", result)
        self.assertIn("**Version:**", result)
        self.assertIn("**License:**", result)
        self.assertIn("GPL-2.0-only", result)
        self.assertIn("Alice", result)
        self.assertIn("**Homepage:**", result)
        self.assertIn("https://git-scm.com/", result)

        # Test with missing fields
        minimal_info = {
            "name": "git",
            "description": "Distributed version control system",
        }
        result = _format_package_info(minimal_info)
        self.assertIn("# git", result)
        self.assertIn("Distributed version control system", result)
        # The implementation always includes a Version field with "Not available"
        self.assertIn("**Version:** Not available", result)

    def test_format_license(self):
        """Test _format_license function."""
        # Test with string license
        self.assertEqual(_format_license("GPL-2.0"), "GPL-2.0")

        # Test with dict license with fullName
        self.assertEqual(_format_license({"fullName": "GPL-2.0-only"}), "GPL-2.0-only")

        # Test with dict license with shortName but no fullName
        # The implementation only checks for fullName, not shortName
        self.assertEqual(_format_license({"shortName": "GPL-2.0"}), "Unknown")

        # Test with dict license with both names
        self.assertEqual(_format_license({"fullName": "GPL-2.0-only", "shortName": "GPL-2.0"}), "GPL-2.0-only")

        # Test with list of licenses
        self.assertEqual(_format_license([{"fullName": "GPL-2.0-only"}, {"fullName": "MIT"}]), "GPL-2.0-only, MIT")

        # Test with empty or None
        self.assertEqual(_format_license(None), "Unknown")
        self.assertEqual(_format_license([]), "Unknown")

    def test_format_maintainers(self):
        """Test _format_maintainers function."""
        # Test with list of maintainers with name and email
        # The implementation only includes the name field, not email
        maintainers = [
            {"name": "Alice", "email": "alice@example.com"},
            {"name": "Bob", "email": "bob@example.com"},
        ]
        result = _format_maintainers(maintainers)
        self.assertIn("Alice", result)
        self.assertIn("Bob", result)
        self.assertEqual(result, "Alice, Bob")

        # Test with list of maintainers with only name
        maintainers = [{"name": "Alice"}, {"name": "Bob"}]
        result = _format_maintainers(maintainers)
        self.assertEqual(result, "Alice, Bob")

        # Test with list of maintainers with only email
        # The implementation only checks for name, not email
        maintainers = [{"email": "alice@example.com"}, {"email": "bob@example.com"}]
        self.assertEqual(_format_maintainers(maintainers), "")

        # Test with empty or None
        self.assertEqual(_format_maintainers(None), "")
        self.assertEqual(_format_maintainers([]), "")

    def test_create_github_link(self):
        """Test _create_github_link function."""
        # Test with valid position
        self.assertEqual(
            _create_github_link("pkgs/applications/version-management/git/default.nix:1"),
            "https://github.com/NixOS/nixpkgs/blob/master/pkgs/applications/version-management/git/default.nix#L1",
        )

        # Test with position without line number
        self.assertEqual(
            _create_github_link("pkgs/applications/version-management/git/default.nix"),
            "https://github.com/NixOS/nixpkgs/blob/master/pkgs/applications/version-management/git/default.nix",
        )

    def test_simple_html_to_markdown(self):
        """Test _simple_html_to_markdown function."""
        # Test with various HTML tags
        html = "<p>This is a <b>bold</b> text with <i>italics</i> and <code>code</code>.</p>"
        result = _simple_html_to_markdown(html)
        self.assertIn("This is a", result)
        self.assertIn("bold", result)
        self.assertIn("italics", result)
        self.assertIn("code", result)

        # Test with links
        html = "Check out <a href='https://example.com'>this link</a>."
        expected = "Check out [this link](https://example.com)."
        self.assertEqual(_simple_html_to_markdown(html), expected)

        # Test with nested tags
        html = "<p>This is <b>bold with <i>italics</i> inside</b>.</p>"
        # The implementation doesn't maintain nested tag structure
        result = _simple_html_to_markdown(html)
        self.assertIn("This is", result)
        self.assertIn("bold with", result)
        self.assertIn("italics", result)
        self.assertIn("inside", result)

        # Test with no HTML
        text = "Plain text without HTML."
        self.assertEqual(_simple_html_to_markdown(text), text)

    def test_get_service_suggestion(self):
        """Test _get_service_suggestion function."""
        # The implementation does not call nixos_search, it just provides text suggestions
        result = _get_service_suggestion("nginx", "unstable")

        # Check that the result contains expected conten
        self.assertIn("Common option patterns for 'nginx' service", result)
        self.assertIn("services.nginx.enable", result)
        self.assertIn("services.nginx.package", result)
        self.assertIn("Example NixOS Configuration", result)
        # Check that it includes a suggestion to use nixos_search
        self.assertIn('nixos_search(query="services.nginx", type="options", channel="unstable")', result)

        # Test with nonexistent service
        result = _get_service_suggestion("nonexistent", "unstable")
        self.assertIn("Common option patterns for 'nonexistent' service", result)
        self.assertIn("services.nonexistent.enable", result)

    def test_format_option_info(self):
        """Test _format_option_info function."""
        info = {
            "name": "services.nginx",
            "description": "Nginx web server configuration",
            "type": "attribute set",
            "default": {},
            "example": {"enable": True},
            "declared_by": ["nixos/modules/services/web-servers/nginx.nix"],
            "readOnly": False,
            "visible": True,
        }

        result = _format_option_info(info, "unstable")
        self.assertIn("# services.nginx", result)
        self.assertIn("**Type:**", result)
        self.assertIn("attribute set", result)
        self.assertIn("**Default:**", result)
        self.assertIn("**Example:**", result)
        self.assertIn("**Example in context:**", result)

        # Test with minimal option info
        result = _format_option_info({"name": "services.nginx"}, "unstable")
        self.assertIn("# services.nginx", result)
        self.assertIn("**Example in context:**", result)

        # Test with minimal info
        minimal_info = {
            "name": "services.nginx",
            "description": "Nginx web server configuration",
        }
        result = _format_option_info(minimal_info, "unstable")
        self.assertIn("# services.nginx", result)
        self.assertIn("Nginx web server configuration", result)
        self.assertNotIn("Type:", result)

    def test_nixos_search_with_context(self):
        """Test nixos_search with provided context."""
        # Mock the search methods to return our test data
        self.mock_context.search_packages.return_value = {
            "packages": [{"name": "git", "version": "2.39.2", "description": "Distributed version control system"}]
        }

        # Test packages search
        result = nixos_search("git", "packages", 10, "unstable", self.mock_context)
        self.mock_context.search_packages.assert_called_once_with("git", limit=10)
        self.assertIn("git", result)

        # Test options search
        self.mock_context.search_packages.reset_mock()
        self.mock_context.search_options.return_value = {
            "options": [{"name": "services.nginx", "description": "Nginx web server configuration"}]
        }
        result = nixos_search("nginx", "options", 10, "unstable", self.mock_context)
        self.mock_context.search_options.assert_called_once_with(
            "nginx", limit=10, additional_terms=["nginx"], quoted_terms=[]
        )
        self.assertIn("services.nginx", result)

        # Test programs search
        self.mock_context.search_options.reset_mock()
        self.mock_context.search_programs.return_value = {
            "packages": [
                {
                    "name": "git",
                    "version": "2.39.2",
                    "description": "Distributed version control system",
                    "programs": ["git"],
                }
            ]
        }
        result = nixos_search("git", "programs", 10, "unstable", self.mock_context)
        self.mock_context.search_programs.assert_called_once_with("git", limit=10)
        self.assertIn("git", result)

        # Test invalid type
        self.mock_context.search_programs.reset_mock()
        result = nixos_search("git", "invalid", 10, "unstable", self.mock_context)
        self.assertIn("Error: Invalid type", result)

    @patch("importlib.import_module")
    def test_nixos_search_with_dynamic_context(self, mock_importlib):
        """Test nixos_search with dynamically imported context."""
        # Setup the mock server module
        mock_server = MagicMock()
        mock_context = MagicMock()
        mock_es_client = MagicMock()
        mock_context.es_client = mock_es_client
        mock_server.get_nixos_context.return_value = mock_context
        mock_importlib.return_value = mock_server

        # Set up mock search results
        mock_es_client.search_packages.return_value = {
            "packages": [{"name": "git", "version": "2.39.2", "description": "Distributed version control system"}]
        }
        mock_context.search_packages.return_value = {
            "packages": [{"name": "git", "version": "2.39.2", "description": "Distributed version control system"}]
        }

        # Call the function without providing a context
        result = nixos_search("git", "packages", 10, "unstable")

        # Verify importlib.import_module was called correctly
        mock_importlib.assert_called_with("mcp_nixos.server")
        self.assertIn("git", result)

    def test_nixos_search_with_none_context(self):
        """Test nixos_search with None context."""
        with patch("importlib.import_module") as mock_importlib:
            # Setup the mock server module to return None
            mock_server = MagicMock()
            mock_server.get_nixos_context.return_value = None
            mock_importlib.return_value = mock_server

            # Call the function without providing a contex
            result = nixos_search("git", "packages", 10, "unstable")

            # Verify error message is returned
            self.assertEqual(result, "Error: NixOS context not available")

    def test_nixos_search_with_multi_word_query(self):
        """Test nixos_search with multi-word query."""
        # Set up mock for contex
        self.mock_context.search_packages.return_value = {"packages": []}

        # Call the function with a multi-word query
        nixos_search("web server", "packages", 10, "unstable", self.mock_context)

        # Verify the search was called with the correct query
        self.mock_context.search_packages.assert_called_once_with("web server", limit=10)

    def test_nixos_info_with_context(self):
        """Test nixos_info with provided context."""
        # Mock the get_package method to return our test data
        self.mock_context.get_package.return_value = {
            "found": True,
            "name": "git",
            "version": "2.39.2",
            "description": "Distributed version control system",
        }

        # Test package info
        result = nixos_info("git", "package", "unstable", self.mock_context)
        self.mock_context.get_package.assert_called_once_with("git")
        self.assertIn("git", result)

        # Test option info
        self.mock_context.get_package.reset_mock()
        self.mock_context.get_option.return_value = {
            "found": True,
            "name": "services.nginx",
            "description": "Nginx web server configuration",
            "type": "attribute set",
            "default": {},
            "example": {"enable": True},
            "declared_by": ["nixos/modules/services/web-servers/nginx.nix"],
        }
        result = nixos_info("services.nginx", "option", "unstable", self.mock_context)
        self.mock_context.get_option.assert_called_once_with("services.nginx")
        self.assertIn("services.nginx", result)

        # Test invalid type
        self.mock_context.get_option.reset_mock()
        result = nixos_info("git", "invalid", "unstable", self.mock_context)
        self.assertIn("Error: 'type' must be 'package' or 'option'", result)

    @patch("importlib.import_module")
    def test_nixos_info_with_dynamic_context(self, mock_importlib):
        """Test nixos_info with dynamically imported context."""
        # Setup the mock server module
        mock_server = MagicMock()
        mock_context = MagicMock()
        mock_es_client = MagicMock()
        mock_context.es_client = mock_es_client
        mock_server.get_nixos_context.return_value = mock_context
        mock_importlib.return_value = mock_server

        # Set up mock package info
        mock_context.get_package.return_value = {
            "found": True,
            "name": "git",
            "version": "2.39.2",
            "description": "Distributed version control system",
        }

        # Call the function without providing a context
        result = nixos_info("git", "package", "unstable")

        # Verify importlib.import_module was called correctly
        mock_importlib.assert_called_with("mcp_nixos.server")
        self.assertIn("git", result)

    def test_nixos_info_with_none_context(self):
        """Test nixos_info with None context."""
        with patch("importlib.import_module") as mock_importlib:
            # Setup the mock server module to return None
            mock_server = MagicMock()
            mock_server.get_nixos_context.return_value = None
            mock_importlib.return_value = mock_server

            # Call the function without providing a contex
            result = nixos_info("git", "package", "unstable")

            # Verify error message is returned
            self.assertEqual(result, "Error: NixOS context not available")

    def test_nixos_stats_with_context(self):
        """Test nixos_stats with provided context."""
        # Set up mock for get_package_stats and count_options
        self.mock_context.get_package_stats.return_value = {
            "aggregations": {
                "channels": {"buckets": [{"key": "unstable", "doc_count": 80000}]},
                "licenses": {"buckets": [{"key": "MIT", "doc_count": 20000}]},
                "platforms": {"buckets": [{"key": "x86_64-linux", "doc_count": 70000}]},
            }
        }
        self.mock_context.count_options.return_value = {"count": 10000}

        # Test stats retrieval
        result = nixos_stats("unstable", self.mock_context)
        self.mock_context.get_package_stats.assert_called_once()
        self.mock_context.count_options.assert_called_once()
        self.assertIn("Package Statistics", result)
        self.assertIn("Total options: 10,000", result)

    @patch("importlib.import_module")
    def test_nixos_stats_with_dynamic_context(self, mock_importlib):
        """Test nixos_stats with dynamically imported context."""
        # Setup the mock server module
        mock_server = MagicMock()
        mock_context = MagicMock()
        mock_es_client = MagicMock()
        mock_context.es_client = mock_es_client
        mock_server.get_nixos_context.return_value = mock_context
        mock_importlib.return_value = mock_server

        # Set up mock stats
        mock_context.get_package_stats.return_value = {
            "aggregations": {
                "channels": {"buckets": [{"key": "unstable", "doc_count": 80000}]},
                "licenses": {"buckets": [{"key": "MIT", "doc_count": 20000}]},
                "platforms": {"buckets": [{"key": "x86_64-linux", "doc_count": 70000}]},
            }
        }
        mock_context.count_options.return_value = {"count": 10000}

        # Call the function without providing a context
        result = nixos_stats("unstable")

        # Verify importlib.import_module was called correctly
        mock_importlib.assert_called_with("mcp_nixos.server")
        self.assertIn("Package Statistics", result)
        self.assertIn("Total options: 10,000", result)

    def test_nixos_stats_with_none_context(self):
        """Test nixos_stats with None context."""
        with patch("importlib.import_module") as mock_importlib:
            # Setup the mock server module to return None
            mock_server = MagicMock()
            mock_server.get_nixos_context.return_value = None
            mock_importlib.return_value = mock_server

            # Call the function without providing a contex
            result = nixos_stats("unstable")

            # Verify error message is returned
            self.assertEqual(result, "Error: NixOS context not available")

    def test_check_request_ready(self):
        """Test check_request_ready function."""
        # Test with string contex
        self.assertTrue(check_request_ready("string_context"))

        # Test with object context that has request_context attribute
        mock_ctx = MagicMock()
        mock_ctx.request_context.lifespan_context.get.return_value = True
        self.assertTrue(check_request_ready(mock_ctx))

        # Test with object context that returns False for is_ready
        mock_ctx.request_context.lifespan_context.get.return_value = False
        self.assertFalse(check_request_ready(mock_ctx))

    def test_register_nixos_tools(self):
        """Test register_nixos_tools function."""
        # Create a mock MCP server
        mock_mcp = MagicMock()

        # Call the function
        register_nixos_tools(mock_mcp)

        # Verify that tool was called for each tool function
        self.assertEqual(mock_mcp.tool.call_count, 3)


if __name__ == "__main__":
    unittest.main()
