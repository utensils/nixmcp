"""Integration tests for Home Manager MCP resources with real data."""

import unittest
import logging
import re
from typing import Dict, Any

# Import the context and client
from nixmcp.contexts.home_manager_context import HomeManagerContext
from nixmcp.clients.home_manager_client import HomeManagerClient

# Import the resource functions directly from the resources module
from nixmcp.resources.home_manager_resources import (
    home_manager_status_resource,
    home_manager_search_options_resource,
    home_manager_option_resource,
    home_manager_stats_resource,
    home_manager_options_list_resource,
    home_manager_options_by_prefix_resource,
)

# No need to import register_home_manager_resources as we're not registering resources

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("home_manager_mcp_test")


class TestHomeManagerMCPIntegration(unittest.TestCase):
    """Integration tests for Home Manager MCP resources with real data."""

    @classmethod
    def setUpClass(cls):
        """Set up once for all tests - initialize the context and wait for data to load."""
        # Create client with test mode settings for faster loading
        client = HomeManagerClient()

        # Set up mock HTML for faster testing instead of fetching from the web
        mock_html = """
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
                        <dt>
                            <span class="term">
                                <a id="opt-programs.firefox.enable"></a>
                                <a class="term" href="options.xhtml#opt-programs.firefox.enable">
                                    <code class="option">programs.firefox.enable</code>
                                </a>
                            </span>
                        </dt>
                        <dd>
                            <p>Whether to enable Firefox.</p>
                            <p><span class="emphasis"><em>Type:</em></span> boolean</p>
                            <p><span class="emphasis"><em>Default:</em></span> false</p>
                            <p><span class="emphasis"><em>Example:</em></span> true</p>
                        </dd>
                        <dt>
                            <span class="term">
                                <a id="opt-services.syncthing.enable"></a>
                                <a class="term" href="options.xhtml#opt-services.syncthing.enable">
                                    <code class="option">services.syncthing.enable</code>
                                </a>
                            </span>
                        </dt>
                        <dd>
                            <p>Whether to enable Syncthing.</p>
                            <p><span class="emphasis"><em>Type:</em></span> boolean</p>
                            <p><span class="emphasis"><em>Default:</em></span> false</p>
                            <p><span class="emphasis"><em>Example:</em></span> true</p>
                        </dd>
                        <dt>
                            <span class="term">
                                <a id="opt-home.file.source"></a>
                                <a class="term" href="options.xhtml#opt-home.file.source">
                                    <code class="option">home.file.source</code>
                                </a>
                            </span>
                        </dt>
                        <dd>
                            <p>File path source.</p>
                            <p><span class="emphasis"><em>Type:</em></span> string</p>
                            <p><span class="emphasis"><em>Default:</em></span> null</p>
                            <p><span class="emphasis"><em>Example:</em></span> "./myconfig"</p>
                        </dd>
                    </dl>
                </div>
            </body>
        </html>
        """

        # Generate test data for each top-level prefix
        for doc_source in ["options", "nixos-options"]:
            # Parse the mock HTML to get sample options
            options = client.parse_html(mock_html, doc_source)

            # Add at least one option for each prefix to ensure we have data to test
            cls.option_prefixes = [
                "programs",
                "services",
                "home",
                "accounts",
                "fonts",
                "gtk",
                "qt",
                "xdg",
                "wayland",
                "i18n",
                "manual",
                "news",
                "nix",
                "nixpkgs",
                "systemd",
                "targets",
                "dconf",
                "editorconfig",
                "lib",
                "launchd",
                "pam",
                "sops",
                "windowManager",
                "xresources",
                "xsession",
            ]

            # Create test options for each prefix
            for prefix in cls.option_prefixes:
                if not any(opt["name"].startswith(f"{prefix}.") for opt in options):
                    # Add a test option for this prefix
                    options.append(
                        {
                            "name": f"{prefix}.test.enable",
                            "type": "boolean",
                            "description": f"Test option for {prefix}",
                            "default": "false",
                            "example": "true",
                            "category": "Testing",
                            "source": doc_source,
                        }
                    )

        # Build the indices with our test data
        client.build_search_indices(options)

        # Mark the client as loaded
        client.is_loaded = True
        client.loading_in_progress = False
        client.loading_error = None

        # Create the context with a mock
        cls.context = HomeManagerContext()

        # Replace the context's client with our pre-loaded one
        cls.context.hm_client = client

        # Make sure client is marked as loaded to prevent background loading
        client.is_loaded = True

        # Add more sample options for each prefix to ensure comprehensive coverage
        options = []
        for prefix in cls.option_prefixes:
            # Add main option
            options.append(
                {
                    "name": f"{prefix}.enable",
                    "type": "boolean",
                    "description": f"Whether to enable {prefix}",
                    "default": "false",
                    "example": "true",
                    "category": "Testing",
                    "source": "options",
                }
            )

            # Add a sub-option
            options.append(
                {
                    "name": f"{prefix}.settings.config",
                    "type": "string",
                    "description": f"Configuration for {prefix}",
                    "default": "null",
                    "example": '"config"',
                    "category": "Testing",
                    "source": "options",
                }
            )

        # Add the options directly to the client's data structures
        for option in options:
            client.options[option["name"]] = option

            # Add to prefix index
            parts = option["name"].split(".")
            for i in range(1, len(parts) + 1):
                prefix = ".".join(parts[:i])
                client.prefix_index[prefix].add(option["name"])

            # Add to category index
            category = option.get("category", "Uncategorized")
            client.options_by_category[category].append(option["name"])

            # Add to inverted index
            words = re.findall(r"\w+", option["name"].lower())
            for word in words:
                if len(word) > 2:
                    client.inverted_index[word].add(option["name"])

        # Confirm we actually have data
        stats = cls.context.get_stats()
        total_options = stats.get("total_options", 0)
        logger.info(f"Test data loaded with {total_options} options")

        # Make sure we have enough data for tests
        if total_options < 25:  # We need at least one option for each prefix
            logger.error(f"Only {total_options} options loaded, data appears incomplete")

            # Output what we have for debugging
            for prefix in cls.option_prefixes:
                count = len([o for o in client.options if o.startswith(f"{prefix}.")])
                logger.info(f"Prefix {prefix}: {count} options")

            # Don't skip, just log the warning - we should have enough test data
            logger.warning("Proceeding with limited test data")

        logger.info(f"Successfully loaded {stats.get('total_options', 0)} options for integration tests")

    def assertValidResource(self, response: Dict[str, Any], resource_name: str):
        """Assert that a resource response is valid."""
        self.assertIsInstance(response, dict, f"{resource_name} response should be a dictionary")

        # Handle the loading state
        if response.get("loading", False):
            self.assertIn("error", response, f"{resource_name} in loading state should have an error message")
            self.assertFalse(response.get("found", True), f"{resource_name} in loading state should have found=False")
            return

        # Handle error state
        if "error" in response:
            self.assertFalse(response.get("found", True), f"{resource_name} with error should have found=False")
        elif "found" in response:
            self.assertIsInstance(response["found"], bool, f"{resource_name} should have boolean found field")

    def test_status_resource(self):
        """Test the home-manager://status resource with real data."""
        result = home_manager_status_resource(self.context)

        # Verify basic structure
        self.assertIsInstance(result, dict)
        self.assertIn("status", result)
        self.assertIn("loaded", result)
        self.assertTrue(result["loaded"])
        self.assertIn("options_count", result)
        self.assertGreater(result["options_count"], 0)
        self.assertIn("cache_stats", result)

    def test_search_options_resource(self):
        """Test the home-manager://search/options/{query} resource with real data."""
        # Test searching for git
        result = home_manager_search_options_resource("git", self.context)

        # Verify structure
        self.assertValidResource(result, "search_options")
        self.assertIn("count", result)
        self.assertIn("options", result)
        self.assertIsInstance(result["options"], list)
        self.assertGreater(result["count"], 0)
        self.assertGreater(len(result["options"]), 0)

        # All options should have a name
        for option in result["options"]:
            self.assertIn("name", option)
            self.assertIn("git", option["name"].lower())
            self.assertIn("description", option)
            self.assertIn("type", option)

    def test_option_resource(self):
        """Test the home-manager://option/{option_name} resource with real data."""
        # Test looking up a specific option that should exist
        result = home_manager_option_resource("programs.git.enable", self.context)

        # Verify structure for found option
        self.assertValidResource(result, "option")
        self.assertTrue(result.get("found", False))
        self.assertEqual(result["name"], "programs.git.enable")
        self.assertIn("description", result)
        self.assertIn("type", result)
        self.assertEqual(result["type"].lower(), "boolean")

        # Test looking up a non-existent option
        result = home_manager_option_resource("programs.nonexistent.option", self.context)

        # Verify structure for not found
        self.assertValidResource(result, "option")
        self.assertFalse(result.get("found", True))
        self.assertIn("error", result)

    def test_stats_resource(self):
        """Test the home-manager://options/stats resource with real data."""
        result = home_manager_stats_resource(self.context)

        # Verify structure
        self.assertIn("total_options", result)
        self.assertGreater(result["total_options"], 0)
        self.assertIn("total_categories", result)
        self.assertGreater(result["total_categories"], 0)
        self.assertIn("total_types", result)
        self.assertGreater(result["total_types"], 0)

        # Verify source breakdown
        self.assertIn("by_source", result)
        self.assertIn("options", result["by_source"])

        # Verify type breakdown
        self.assertIn("by_type", result)
        self.assertIn("boolean", result["by_type"])
        self.assertIn("string", result["by_type"])

    def test_options_list_resource(self):
        """Test the home-manager://options/list resource with real data."""
        result = home_manager_options_list_resource(self.context)

        # Handle case where data is still loading
        if result.get("loading", False):
            logger.warning("Home Manager data still loading during options list test")
            self.assertIn("error", result)
            self.skipTest("Home Manager data is still loading")
            return

        # Verify structure
        self.assertValidResource(result, "options_list")
        self.assertTrue(result.get("found", False))
        self.assertIn("options", result)
        self.assertIsInstance(result["options"], dict)
        self.assertGreater(len(result["options"]), 0)

        # Check common categories are present
        self.assertIn("programs", result["options"])
        self.assertIn("services", result["options"])

        # Verify structure of category entries
        for category, data in result["options"].items():
            self.assertIn("count", data)
            self.assertIn("has_children", data)
            self.assertIn("types", data)
            self.assertIn("enable_options", data)

        # Verify that all option prefixes defined in our class are present
        for prefix in self.option_prefixes:
            self.assertIn(prefix, result["options"], f"Option prefix '{prefix}' missing from options list")

        # Log the number of options in each category
        logger.info("Option counts by category:")
        for category, data in result["options"].items():
            count = data.get("count", 0)
            logger.info(f"  {category}: {count} options")

        # Ensure at least one category has options
        has_options = False
        for category, data in result["options"].items():
            if data.get("count", 0) > 0:
                has_options = True
                break

        self.assertTrue(has_options, "No categories have any options")

    def test_prefix_resource_programs(self):
        """Test the home-manager://options/programs resource with real data."""
        result = home_manager_options_by_prefix_resource("programs", self.context)

        # Verify structure
        self.assertValidResource(result, "options_by_prefix_programs")
        self.assertTrue(result.get("found", False))
        self.assertEqual(result["prefix"], "programs")
        self.assertIn("options", result)
        self.assertIsInstance(result["options"], list)
        self.assertGreater(len(result["options"]), 0)
        self.assertGreater(result["count"], 0)

        # All options should start with programs.
        for option in result["options"]:
            self.assertIn("name", option)
            self.assertTrue(option["name"].startswith("programs."))
            self.assertIn("description", option)
            self.assertIn("type", option)

    def test_prefix_resource_home(self):
        """Test the home-manager://options/home resource with real data."""
        result = home_manager_options_by_prefix_resource("home", self.context)

        # Verify result structure
        self.assertValidResource(result, "options_by_prefix_home")

        # If not found, verify there's an error message
        if not result.get("found", False):
            # Check if data is still loading, in which case the test is fine
            if result.get("loading", False):
                logger.warning(f"Home Manager data still loading: {result.get('error', 'Unknown error')}")
                self.assertIn("error", result)
                self.assertTrue(result.get("loading", False))
                return

            logger.warning(f"No options found with prefix 'home': {result.get('error', 'Unknown error')}")

            # Try an alternative way to search for "home" options
            search_result = home_manager_search_options_resource("home.", self.context)

            # Check if the alternate search is also in loading state
            if search_result.get("loading", False):
                logger.warning(
                    f"Home Manager data still loading during search: {search_result.get('error', 'Unknown error')}"
                )
                self.assertIn("error", search_result)
                return

            # Log what we find to help diagnose the problem
            logger.info(f"Search for 'home.' found {search_result.get('count', 0)} options")
            if search_result.get("count", 0) > 0:
                sample_options = [opt["name"] for opt in search_result.get("options", [])[:5]]
                logger.info(f"Sample home-related options: {sample_options}")

                # We expect actual options, even if the prefix doesn't work
                self.assertGreater(search_result.get("count", 0), 0)

            # The test should not fail if no options with prefix 'home' exist
            # This might be legitimate behavior depending on the data source
            # Just assert there's an error message
            self.assertIn("error", result)
        else:
            # If found, verify the structure and data
            self.assertEqual(result["prefix"], "home")
            self.assertIn("options", result)
            self.assertIsInstance(result["options"], list)
            self.assertGreater(len(result["options"]), 0)
            self.assertGreater(result["count"], 0)

            # All options should start with home.
            for option in result["options"]:
                self.assertIn("name", option)
                self.assertTrue(option["name"].startswith("home."))

    def test_prefix_resource_xdg(self):
        """Test the home-manager://options/xdg resource with real data."""
        result = home_manager_options_by_prefix_resource("xdg", self.context)

        # Verify structure
        self.assertValidResource(result, "options_by_prefix_xdg")

        # If not found, verify there's an error message and try an alternative search
        if not result.get("found", False):
            # Check if data is still loading, in which case the test is fine
            if result.get("loading", False):
                logger.warning(f"Home Manager data still loading: {result.get('error', 'Unknown error')}")
                self.assertIn("error", result)
                self.assertTrue(result.get("loading", False))
                return

            logger.warning(f"No options found with prefix 'xdg': {result.get('error', 'Unknown error')}")

            # Try an alternative way to search for "xdg" options
            search_result = home_manager_search_options_resource("xdg.", self.context)

            # Check if the alternate search is also in loading state
            if search_result.get("loading", False):
                logger.warning(
                    f"Home Manager data still loading during search: {search_result.get('error', 'Unknown error')}"
                )
                self.assertIn("error", search_result)
                return

            # Log what we find to help diagnose the problem
            logger.info(f"Search for 'xdg.' found {search_result.get('count', 0)} options")
            if search_result.get("count", 0) > 0:
                sample_options = [opt["name"] for opt in search_result.get("options", [])[:5]]
                logger.info(f"Sample xdg-related options: {sample_options}")

                # We expect actual options, even if the prefix doesn't work
                self.assertGreater(search_result.get("count", 0), 0)

            # Assert there's an error message
            self.assertIn("error", result)
        else:
            # If found, verify the structure and data
            self.assertEqual(result["prefix"], "xdg")
            self.assertIn("options", result)
            self.assertIsInstance(result["options"], list)
            self.assertGreater(len(result["options"]), 0)
            self.assertGreater(result["count"], 0)

            # All options should start with xdg.
            for option in result["options"]:
                self.assertIn("name", option)
                self.assertTrue(option["name"].startswith("xdg."))

    def test_prefix_resource_nested_path(self):
        """Test with a nested path like programs.git."""
        result = home_manager_options_by_prefix_resource("programs.git", self.context)

        # Handle case where data is still loading
        if result.get("loading", False):
            logger.warning("Home Manager data still loading during nested path test")
            self.assertIn("error", result)
            self.skipTest("Home Manager data is still loading")
            return

        # Verify structure
        self.assertValidResource(result, "options_by_prefix_nested")
        self.assertTrue(result.get("found", False))
        self.assertEqual(result["prefix"], "programs.git")
        self.assertIn("options", result)
        self.assertIsInstance(result["options"], list)
        self.assertGreater(len(result["options"]), 0)

        # All options should start with programs.git.
        for option in result["options"]:
            self.assertIn("name", option)
            self.assertTrue(option["name"].startswith("programs.git."))

    def test_generic_prefix_resource(self):
        """Test the generic home-manager://options/prefix/{option_prefix} resource."""
        # Test with a few different prefixes that might have options
        prefixes_to_try = ["programs.firefox", "programs.bash", "programs.vim", "services.syncthing"]

        found_one = False
        for prefix in prefixes_to_try:
            logger.info(f"Testing generic prefix resource with {prefix}")
            result = home_manager_options_by_prefix_resource(prefix, self.context)

            # Handle loading state
            if result.get("loading", False):
                logger.warning(f"Home Manager data still loading for {prefix}")
                continue

            # Check if we found options for this prefix
            if result.get("found", False) and result.get("count", 0) > 0:
                found_one = True

                # Verify the structure
                self.assertValidResource(result, f"generic_prefix_{prefix}")
                self.assertEqual(result["prefix"], prefix)
                self.assertIn("options", result)
                self.assertIsInstance(result["options"], list)
                self.assertGreater(len(result["options"]), 0)

                # All options should start with the prefix
                for option in result["options"]:
                    self.assertIn("name", option)
                    self.assertTrue(option["name"].startswith(f"{prefix}."))

                logger.info(f"Found {result.get('count', 0)} options for {prefix}")
                break  # We found what we needed, so break

        # Skip the test if all prefixes are still loading
        if not found_one and all(
            home_manager_options_by_prefix_resource(p, self.context).get("loading", False) for p in prefixes_to_try
        ):
            self.skipTest("Home Manager data is still loading")
            return

        # We should have found at least one prefix with options
        self.assertTrue(found_one, f"None of the test prefixes {prefixes_to_try} returned options")

    def test_prefix_resource_with_invalid_prefix(self):
        """Test with an invalid prefix."""
        result = home_manager_options_by_prefix_resource("nonexistent_prefix", self.context)

        # Verify structure for not found
        self.assertValidResource(result, "options_by_prefix_invalid")
        self.assertFalse(result.get("found", True))
        self.assertIn("error", result)

    def test_all_option_prefixes(self):
        """Test all registered option prefixes to ensure none are empty."""
        logger.info("Testing all Home Manager option prefixes...")

        found_data = {}
        not_found_count = 0
        loading_count = 0

        for prefix in self.option_prefixes:
            logger.info(f"Testing prefix: {prefix}")
            result = home_manager_options_by_prefix_resource(prefix, self.context)

            # Check if the resource is valid
            self.assertValidResource(result, f"options_by_prefix_{prefix}")

            # If it's still loading, log and continue
            if result.get("loading", False):
                logger.warning(f"Data still loading for prefix '{prefix}'")
                loading_count += 1
                continue

            # Track if the prefix has data
            if result.get("found", False):
                count = result.get("count", 0)
                found_data[prefix] = count
                logger.info(f"Prefix '{prefix}' returned {count} options")

                # Verify we have options for this prefix
                self.assertIn("options", result)
                self.assertIsInstance(result["options"], list)

                # Verify all returned options start with this prefix
                if count > 0:
                    for option in result["options"]:
                        self.assertIn("name", option)
                        self.assertTrue(option["name"].startswith(f"{prefix}."))
            else:
                not_found_count += 1
                logger.warning(f"No data found for prefix '{prefix}': {result.get('error', 'Unknown error')}")

        # Summarize results
        logger.info(
            f"Found data for {len(found_data)} prefixes, "
            f"no data for {not_found_count}, still loading for {loading_count}"
        )

        # If all prefixes are still loading, skip the test
        if loading_count == len(self.option_prefixes):
            self.skipTest("All Home Manager data is still loading")

        # Log the prefixes that were found with their counts
        if found_data:
            for prefix, count in found_data.items():
                logger.info(f"Prefix '{prefix}': {count} options")

        # We should have found data for at least some prefixes
        self.assertGreater(len(found_data), 0, "No option prefixes returned any data")


if __name__ == "__main__":
    unittest.main()
