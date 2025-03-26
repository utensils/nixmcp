import unittest
import logging
from unittest.mock import patch, MagicMock
import time
import threading

# Import the server module
from nixmcp.server import HomeManagerClient, HomeManagerContext

# Disable logging during tests
logging.disable(logging.CRITICAL)

"""
Test approach:

This test suite tests the Home Manager integration in NixMCP. It uses mocking to avoid
making actual network requests during tests, focusing on ensuring that:

1. The HTML parsing logic works correctly
2. The in-memory search indexing works correctly
3. The background loading mechanism works correctly
4. The MCP resources and tools work as expected

The tests are designed to be fast and reliable, without requiring internet access.
"""


class TestHomeManagerClient(unittest.TestCase):
    """Test the HomeManagerClient class using mocks for network requests."""

    def setUp(self):
        """Set up the test environment."""
        # Create a mock for the requests.get method
        self.requests_get_patcher = patch("requests.get")
        self.mock_requests_get = self.requests_get_patcher.start()

        # Set up a mock response for HTML content
        # Use the actual variablelist/dl/dt/dd structure from Home Manager docs
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <body>
                <div class="variablelist">
                    <dl class="variablelist">
                        <dt>
                            <span class="term">
                                <a id="opt-programs.git.enable"></a>
                                <a class="term" href="options.xhtml#opt-programs.git.enable">
                                    <code class="option">programs.git.enable</code>
                                </a>
                            </span>
                        </dt>
                        <dd>
                            <p>Whether to enable Git.</p>
                            <p><span class="emphasis"><em>Type:</em></span> boolean</p>
                            <p><span class="emphasis"><em>Default:</em></span> false</p>
                            <p><span class="emphasis"><em>Example:</em></span> true</p>
                        </dd>
                        <dt>
                            <span class="term">
                                <a id="opt-programs.git.userName"></a>
                                <a class="term" href="options.xhtml#opt-programs.git.userName">
                                    <code class="option">programs.git.userName</code>
                                </a>
                            </span>
                        </dt>
                        <dd>
                            <p>Your Git username.</p>
                            <p><span class="emphasis"><em>Type:</em></span> string</p>
                            <p><span class="emphasis"><em>Default:</em></span> null</p>
                            <p><span class="emphasis"><em>Example:</em></span> "John Doe"</p>
                        </dd>
                    </dl>
                </div>
            </body>
        </html>
        """
        mock_response.raise_for_status = MagicMock()
        self.mock_requests_get.return_value = mock_response

        # Create the client
        self.client = HomeManagerClient()

        # Override the cache to make it predictable for testing
        self.client.cache.clear()

    def tearDown(self):
        """Clean up after the test."""
        self.requests_get_patcher.stop()

    def test_fetch_url(self):
        """Test fetching HTML content from a URL."""
        # Fetch a URL
        url = "https://example.com/options.xhtml"
        content = self.client.fetch_url(url)

        # Verify the mock was called with the expected URL
        self.mock_requests_get.assert_called_once_with(
            url, timeout=(self.client.connect_timeout, self.client.read_timeout), headers={"User-Agent": "NixMCP/0.1.1"}
        )

        # Verify the content was returned
        self.assertIsNotNone(content)
        self.assertIn('<div class="variablelist">', content)

    def test_parse_html(self):
        """Test parsing HTML content."""
        # Parse the mock HTML content
        html = self.mock_requests_get.return_value.text
        options = self.client.parse_html(html, "test")

        # Verify the options were parsed correctly
        self.assertEqual(len(options), 2)

        # Check the first option
        option1 = options[0]
        self.assertEqual(option1["name"], "programs.git.enable")
        self.assertEqual(option1["type"], "boolean")
        self.assertEqual(option1["description"], "Whether to enable Git.")
        self.assertEqual(option1["default"], "false")
        self.assertEqual(option1["example"], "true")
        self.assertEqual(option1["category"], "Uncategorized")  # No h3 heading in our mock HTML
        self.assertEqual(option1["source"], "test")

        # Check the second option
        option2 = options[1]
        self.assertEqual(option2["name"], "programs.git.userName")
        self.assertEqual(option2["type"], "string")
        self.assertEqual(option2["description"], "Your Git username.")
        self.assertEqual(option2["default"], "null")
        self.assertEqual(option2["example"], '"John Doe"')

    def test_build_search_indices(self):
        """Test building search indices."""
        # Create sample options
        options = [
            {
                "name": "programs.git.enable",
                "type": "boolean",
                "description": "Whether to enable Git.",
                "category": "Version Control",
            },
            {
                "name": "programs.git.userName",
                "type": "string",
                "description": "Your Git username.",
                "category": "Version Control",
            },
            {
                "name": "programs.firefox.enable",
                "type": "boolean",
                "description": "Whether to enable Firefox.",
                "category": "Web Browsers",
            },
        ]

        # Build the indices
        self.client.build_search_indices(options)

        # Verify options index
        self.assertEqual(len(self.client.options), 3)
        self.assertIn("programs.git.enable", self.client.options)
        self.assertIn("programs.git.userName", self.client.options)
        self.assertIn("programs.firefox.enable", self.client.options)

        # Verify category index
        self.assertEqual(len(self.client.options_by_category), 2)
        self.assertIn("Version Control", self.client.options_by_category)
        self.assertIn("Web Browsers", self.client.options_by_category)
        self.assertEqual(len(self.client.options_by_category["Version Control"]), 2)
        self.assertEqual(len(self.client.options_by_category["Web Browsers"]), 1)

        # Verify inverted index
        self.assertIn("git", self.client.inverted_index)
        self.assertIn("enable", self.client.inverted_index)
        self.assertIn("firefox", self.client.inverted_index)
        self.assertIn("programs.git", self.client.prefix_index)
        self.assertIn("programs.firefox", self.client.prefix_index)

    def test_search_options(self):
        """Test searching for options."""
        # Create sample options
        options = [
            {
                "name": "programs.git.enable",
                "type": "boolean",
                "description": "Whether to enable Git.",
                "category": "Version Control",
            },
            {
                "name": "programs.git.userName",
                "type": "string",
                "description": "Your Git username.",
                "category": "Version Control",
            },
            {
                "name": "programs.firefox.enable",
                "type": "boolean",
                "description": "Whether to enable Firefox.",
                "category": "Web Browsers",
            },
        ]

        # Build the indices
        self.client.build_search_indices(options)
        self.client.is_loaded = True

        # Search for git
        results = self.client.search_options("git")

        # Verify the results
        self.assertEqual(results["count"], 2)
        self.assertEqual(len(results["options"]), 2)

        # Verify the options are ordered by score
        self.assertEqual(results["options"][0]["name"], "programs.git.enable")
        self.assertEqual(results["options"][1]["name"], "programs.git.userName")

        # Search for firefox
        results = self.client.search_options("firefox")

        # Verify the results
        self.assertEqual(results["count"], 1)
        self.assertEqual(len(results["options"]), 1)
        self.assertEqual(results["options"][0]["name"], "programs.firefox.enable")

        # Search by prefix
        results = self.client.search_options("programs.git")

        # Verify the results
        self.assertEqual(results["count"], 2)
        self.assertEqual(len(results["options"]), 2)

        # Search by prefix with wildcard
        results = self.client.search_options("programs.git.*")

        # Verify the results
        self.assertEqual(results["count"], 2)
        self.assertEqual(len(results["options"]), 2)

    def test_hierarchical_path_searching(self):
        """Test searching for options with hierarchical paths."""
        # Create sample options with hierarchical paths
        options = [
            # Git options
            {
                "name": "programs.git.enable",
                "type": "boolean",
                "description": "Whether to enable Git.",
                "category": "Version Control",
            },
            {
                "name": "programs.git.userName",
                "type": "string",
                "description": "Your Git username.",
                "category": "Version Control",
            },
            {
                "name": "programs.git.userEmail",
                "type": "string",
                "description": "Your Git email.",
                "category": "Version Control",
            },
            {
                "name": "programs.git.signing.key",
                "type": "string",
                "description": "GPG key to use for signing commits.",
                "category": "Version Control",
            },
            {
                "name": "programs.git.signing.signByDefault",
                "type": "boolean",
                "description": "Whether to sign commits by default.",
                "category": "Version Control",
            },
            # Firefox options
            {
                "name": "programs.firefox.enable",
                "type": "boolean",
                "description": "Whether to enable Firefox.",
                "category": "Web Browsers",
            },
            {
                "name": "programs.firefox.package",
                "type": "package",
                "description": "Firefox package to use.",
                "category": "Web Browsers",
            },
            {
                "name": "programs.firefox.profiles.default.id",
                "type": "string",
                "description": "Firefox default profile ID.",
                "category": "Web Browsers",
            },
            {
                "name": "programs.firefox.profiles.default.settings",
                "type": "attribute set",
                "description": "Firefox default profile settings.",
                "category": "Web Browsers",
            },
        ]

        # Build the indices
        self.client.build_search_indices(options)
        self.client.is_loaded = True

        # Test nested hierarchical path search
        results = self.client.search_options("programs.git.signing")

        # Verify the results
        self.assertEqual(results["count"], 2)
        self.assertEqual(len(results["options"]), 2)
        self.assertIn(results["options"][0]["name"], ["programs.git.signing.key", "programs.git.signing.signByDefault"])
        self.assertIn(results["options"][1]["name"], ["programs.git.signing.key", "programs.git.signing.signByDefault"])

        # Test deep hierarchical path with wildcard
        results = self.client.search_options("programs.firefox.profiles.*")

        # Verify the results
        self.assertEqual(results["count"], 2)
        self.assertEqual(len(results["options"]), 2)
        self.assertIn(
            results["options"][0]["name"],
            ["programs.firefox.profiles.default.id", "programs.firefox.profiles.default.settings"],
        )
        self.assertIn(
            results["options"][1]["name"],
            ["programs.firefox.profiles.default.id", "programs.firefox.profiles.default.settings"],
        )

        # Test specific nested path segment
        results = self.client.search_options("programs.firefox.profiles.default")

        # Verify the results
        self.assertEqual(results["count"], 2)
        self.assertEqual(len(results["options"]), 2)
        self.assertEqual(results["options"][0]["name"], "programs.firefox.profiles.default.id")
        self.assertEqual(results["options"][1]["name"], "programs.firefox.profiles.default.settings")

    def test_get_option(self):
        """Test getting a specific option."""
        # Create sample options
        options = [
            {
                "name": "programs.git.enable",
                "type": "boolean",
                "description": "Whether to enable Git.",
                "category": "Version Control",
                "default": "false",
                "example": "true",
            },
            {
                "name": "programs.git.userName",
                "type": "string",
                "description": "Your Git username.",
                "category": "Version Control",
                "default": None,
                "example": '"John Doe"',
            },
        ]

        # Build the indices
        self.client.build_search_indices(options)
        self.client.is_loaded = True

        # Get an option
        result = self.client.get_option("programs.git.enable")

        # Verify the result
        self.assertTrue(result["found"])
        self.assertEqual(result["name"], "programs.git.enable")
        self.assertEqual(result["type"], "boolean")
        self.assertEqual(result["description"], "Whether to enable Git.")
        self.assertEqual(result["category"], "Version Control")
        self.assertEqual(result["default"], "false")
        self.assertEqual(result["example"], "true")

        # Verify related options
        self.assertIn("related_options", result)
        self.assertEqual(len(result["related_options"]), 1)
        self.assertEqual(result["related_options"][0]["name"], "programs.git.userName")

        # Test getting a non-existent option
        result = self.client.get_option("programs.nonexistent")

        # Verify the result
        self.assertFalse(result["found"])
        self.assertIn("error", result)

    def test_get_stats(self):
        """Test getting statistics."""
        # Create sample options
        options = [
            {
                "name": "programs.git.enable",
                "type": "boolean",
                "description": "Whether to enable Git.",
                "category": "Version Control",
                "source": "options",
            },
            {
                "name": "programs.git.userName",
                "type": "string",
                "description": "Your Git username.",
                "category": "Version Control",
                "source": "options",
            },
            {
                "name": "programs.firefox.enable",
                "type": "boolean",
                "description": "Whether to enable Firefox.",
                "category": "Web Browsers",
                "source": "nixos-options",
            },
        ]

        # Build the indices
        self.client.build_search_indices(options)
        self.client.is_loaded = True

        # Get stats
        stats = self.client.get_stats()

        # Verify the stats
        self.assertEqual(stats["total_options"], 3)
        self.assertEqual(stats["total_categories"], 2)
        self.assertEqual(stats["total_types"], 2)

        # Verify source stats
        self.assertEqual(len(stats["by_source"]), 2)
        self.assertEqual(stats["by_source"]["options"], 2)
        self.assertEqual(stats["by_source"]["nixos-options"], 1)

        # Verify category stats
        self.assertEqual(len(stats["by_category"]), 2)
        self.assertEqual(stats["by_category"]["Version Control"], 2)
        self.assertEqual(stats["by_category"]["Web Browsers"], 1)

        # Verify type stats
        self.assertEqual(len(stats["by_type"]), 2)
        self.assertEqual(stats["by_type"]["boolean"], 2)
        self.assertEqual(stats["by_type"]["string"], 1)


class TestHomeManagerContext(unittest.TestCase):
    """Test the HomeManagerContext class using mocks."""

    def setUp(self):
        """Set up the test environment."""
        # Create a mock for the HomeManagerClient
        self.client_patcher = patch("nixmcp.server.HomeManagerClient")
        self.MockClient = self.client_patcher.start()

        # Create a mock client instance
        self.mock_client = MagicMock()
        self.MockClient.return_value = self.mock_client

        # Configure the mock client
        self.mock_client.is_loaded = True
        self.mock_client.loading_lock = threading.RLock()

        # Create the context
        self.context = HomeManagerContext()

    def tearDown(self):
        """Clean up after the test."""
        self.client_patcher.stop()

    def test_get_status(self):
        """Test getting status."""
        # Configure the mock
        mock_stats = {"total_options": 100}
        mock_cache_stats = {"hits": 10, "misses": 5}
        self.mock_client.get_stats.return_value = mock_stats
        self.mock_client.cache.get_stats.return_value = mock_cache_stats

        # Get status
        status = self.context.get_status()

        # Verify the status
        self.assertEqual(status["status"], "ok")
        self.assertTrue(status["loaded"])
        self.assertEqual(status["options_count"], 100)
        self.assertEqual(status["cache_stats"], mock_cache_stats)

    def test_search_options(self):
        """Test searching options."""
        # Configure the mock
        mock_results = {"count": 2, "options": [{"name": "test1"}, {"name": "test2"}]}
        self.mock_client.search_options.return_value = mock_results

        # Search options
        results = self.context.search_options("test", 10)

        # Verify the results
        self.assertEqual(results, mock_results)
        self.mock_client.search_options.assert_called_once_with("test", 10)

    def test_get_option(self):
        """Test getting an option."""
        # Configure the mock
        mock_option = {"name": "test", "found": True}
        self.mock_client.get_option.return_value = mock_option

        # Get option
        option = self.context.get_option("test")

        # Verify the option
        self.assertEqual(option, mock_option)
        self.mock_client.get_option.assert_called_once_with("test")

    def test_get_stats(self):
        """Test getting stats."""
        # Configure the mock
        mock_stats = {"total_options": 100}
        self.mock_client.get_stats.return_value = mock_stats

        # Get stats
        stats = self.context.get_stats()

        # Verify the stats
        self.assertEqual(stats, mock_stats)
        self.mock_client.get_stats.assert_called_once()


class TestHomeManagerTools(unittest.TestCase):
    """Test the Home Manager MCP tools."""

    def setUp(self):
        """Set up the test environment."""
        # Create a mock for the HomeManagerContext
        self.context_patcher = patch("nixmcp.server.home_manager_context")
        self.mock_context = self.context_patcher.start()

        # Import the tool functions
        from nixmcp.server import home_manager_search, home_manager_info, home_manager_stats

        self.search_tool = home_manager_search
        self.info_tool = home_manager_info
        self.stats_tool = home_manager_stats

    def tearDown(self):
        """Clean up after the test."""
        self.context_patcher.stop()

    def test_home_manager_search(self):
        """Test the home_manager_search tool."""
        # Configure the mock
        self.mock_context.search_options.return_value = {
            "count": 2,
            "options": [
                {
                    "name": "programs.git.enable",
                    "type": "boolean",
                    "description": "Whether to enable Git.",
                    "category": "Version Control",
                },
                {
                    "name": "programs.git.userName",
                    "type": "string",
                    "description": "Your Git username.",
                    "category": "Version Control",
                },
            ],
        }

        # Call the tool
        result = self.search_tool("git")

        # Verify the result
        self.assertIn("Found 2 Home Manager options for", result)
        self.assertIn("programs.git.enable", result)
        self.assertIn("programs.git.userName", result)
        self.assertIn("Version Control", result)
        self.assertIn("Type: boolean", result)
        self.assertIn("Type: string", result)
        self.assertIn("Whether to enable Git", result)
        self.assertIn("Your Git username", result)

        # Verify the context was called correctly
        self.mock_context.search_options.assert_called_once()

    def test_home_manager_info(self):
        """Test the home_manager_info tool."""
        # Configure the mock
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
                {"name": "programs.git.userName", "type": "string", "description": "Your Git username."}
            ],
        }

        # Call the tool
        result = self.info_tool("programs.git.enable")

        # Verify the result
        self.assertIn("# programs.git.enable", result)
        self.assertIn("**Description:** Whether to enable Git", result)
        self.assertIn("**Type:** boolean", result)
        self.assertIn("**Default:** false", result)
        self.assertIn("**Example:**", result)
        self.assertIn("**Category:** Version Control", result)
        self.assertIn("**Source:** options", result)
        self.assertIn("## Related Options", result)
        self.assertIn("`programs.git.userName`", result)
        self.assertIn("## Example Home Manager Configuration", result)

        # Verify the context was called correctly
        self.mock_context.get_option.assert_called_once_with("programs.git.enable")

    def test_home_manager_stats(self):
        """Test the home_manager_stats tool."""
        # Configure the mock
        self.mock_context.get_stats.return_value = {
            "total_options": 100,
            "total_categories": 10,
            "total_types": 5,
            "by_source": {"options": 60, "nixos-options": 40},
            "by_category": {"Version Control": 20, "Web Browsers": 15, "Text Editors": 10},
            "by_type": {"boolean": 50, "string": 30, "integer": 10, "list": 5, "attribute set": 5},
            "index_stats": {"words": 500, "prefixes": 200, "hierarchical_parts": 300},
        }

        # Call the tool
        result = self.stats_tool()

        # Verify the result
        self.assertIn("# Home Manager Option Statistics", result)
        self.assertIn("Total options: 100", result)
        self.assertIn("Categories: 10", result)
        self.assertIn("Option types: 5", result)
        self.assertIn("## Distribution by Source", result)
        self.assertIn("options: 60", result)
        self.assertIn("nixos-options: 40", result)
        self.assertIn("## Top Categories", result)
        self.assertIn("Version Control: 20", result)
        self.assertIn("Web Browsers: 15", result)
        self.assertIn("## Distribution by Type", result)
        self.assertIn("boolean: 50", result)
        self.assertIn("string: 30", result)
        self.assertIn("## Index Statistics", result)
        self.assertIn("Words indexed: 500", result)
        self.assertIn("Prefix paths: 200", result)
        self.assertIn("Hierarchical parts: 300", result)

        # Verify the context was called correctly
        self.mock_context.get_stats.assert_called_once()


if __name__ == "__main__":
    unittest.main()
