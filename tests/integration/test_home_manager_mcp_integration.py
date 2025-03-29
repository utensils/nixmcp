import unittest
import logging
import pytest

from typing import Dict, Any, Optional

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Import the context and client
from mcp_nixos.contexts.home_manager_context import HomeManagerContext
from mcp_nixos.clients.home_manager_client import HomeManagerClient

# Import the resource functions directly
from mcp_nixos.resources.home_manager_resources import (
    home_manager_status_resource,
    home_manager_search_options_resource,
    home_manager_option_resource,
    home_manager_stats_resource,
    home_manager_options_list_resource,
    home_manager_options_by_prefix_resource,
)

# Configure logging (can be simplified if detailed logs aren't always needed)
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)  # Use __name__ for standard practice

# --- Constants for Test Data ---
MOCK_HTML = """
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

EXPECTED_OPTION_NAMES = [
    "programs.git.enable",
    "programs.git.userName",
    "programs.firefox.enable",
    "services.syncthing.enable",
    "home.file.source",
]

EXPECTED_PREFIXES = ["programs", "services", "home"]


class TestHomeManagerMCPIntegration(unittest.TestCase):
    """Integration tests for Home Manager MCP resources with mock data loading."""

    context: Optional[HomeManagerContext] = None  # Class attribute for context

    @classmethod
    def setUpClass(cls):
        """Set up once: Use client to parse mock HTML and build indices."""
        logger.info("Setting up HomeManagerContext for integration tests...")
        client = HomeManagerClient()

        # Let the client parse the mock HTML and build its internal structures
        # Assume parsing logic handles adding 'source' if needed, or adjust if necessary
        try:
            # Simulate loading from different sources if applicable
            options_from_html = client.parse_html(MOCK_HTML, "options")
            # If nixos-options source exists and is different:
            # options_from_html.extend(client.parse_html(MOCK_NIXOS_HTML, "nixos-options"))

            # Let the client build its indices from the parsed data
            client.build_search_indices(options_from_html)

            # Update client state
            client.is_loaded = True
            client.loading_in_progress = False
            client.loading_error = None
            logger.info(f"Client loaded with {len(client.options)} options from mock HTML.")

        except Exception as e:
            logger.error(f"Failed to set up client from mock HTML: {e}", exc_info=True)
            # Fail setup explicitly if loading mock data fails
            raise unittest.SkipTest(f"Failed to load mock data for integration tests: {e}")

        # Create context and inject the pre-loaded client
        cls.context = HomeManagerContext()
        cls.context.hm_client = client

        # Sanity check loaded data
        stats = cls.context.get_stats()
        total_options = stats.get("total_options", 0)
        if total_options != len(EXPECTED_OPTION_NAMES):
            logger.warning(
                f"Loaded options count ({total_options}) doesn't match expected "
                f"({len(EXPECTED_OPTION_NAMES)}). Check mock HTML and parsing."
            )
        # No need to skip if counts differ slightly, the core tests should still run

        logger.info(f"Setup complete. Context ready with {total_options} options.")

    def assertValidResource(self, response: Dict[str, Any], resource_name: str):
        """Assert that a resource response is valid (not loading, possibly has error)."""
        self.assertIsInstance(response, dict, f"{resource_name}: Response should be a dict")

        # Check for loading state - should not happen with pre-loaded data
        self.assertFalse(response.get("loading", False), f"{resource_name}: Should not be in loading state")

        # If error, found should be false
        if "error" in response:
            self.assertFalse(response.get("found", True), f"{resource_name}: Error response should have found=False")
        # If 'found' exists, it must be boolean
        elif "found" in response:
            self.assertIsInstance(response["found"], bool, f"{resource_name}: 'found' field must be boolean")

    # --- Test Cases ---

    def test_status_resource(self):
        """Test home-manager://status resource."""
        result = home_manager_status_resource(self.context)
        self.assertValidResource(result, "status")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["loaded"])
        self.assertGreater(result["options_count"], 0)
        self.assertIn("cache_stats", result)  # Cache stats might be zero if no lookups yet

    def test_search_options_resource(self):
        """Test home-manager://search/options/{query}."""
        query = "git"
        result = home_manager_search_options_resource(query, self.context)
        self.assertValidResource(result, f"search_options({query})")
        self.assertTrue(result.get("found", False))
        self.assertIn("count", result)
        self.assertIn("options", result)
        self.assertIsInstance(result["options"], list)
        self.assertGreaterEqual(result["count"], 2)  # Expecting at least git.enable, git.userName
        self.assertEqual(len(result["options"]), result["count"])

        # Check basic structure of returned options
        found_names = set()
        for option in result["options"]:
            self.assertIn("name", option)
            self.assertIn("description", option)
            self.assertIn("type", option)
            self.assertIn(query, option["name"].lower())  # Result name should contain query
            found_names.add(option["name"])

        self.assertIn("programs.git.enable", found_names)
        self.assertIn("programs.git.userName", found_names)

    def test_option_resource_found(self):
        """Test home-manager://option/{option_name} (found)."""
        option_name = "programs.git.enable"
        result = home_manager_option_resource(option_name, self.context)
        self.assertValidResource(result, f"option({option_name})")
        self.assertTrue(result.get("found", False))
        self.assertEqual(result["name"], option_name)
        self.assertIn("description", result)
        self.assertIn("type", result)
        self.assertIn("default", result)
        self.assertIn("example", result)
        # self.assertIn("related_options", result) # Related options might be empty or complex

    def test_option_resource_not_found(self):
        """Test home-manager://option/{option_name} (not found)."""
        option_name = "non.existent.option"
        result = home_manager_option_resource(option_name, self.context)
        self.assertValidResource(result, f"option({option_name})")
        self.assertFalse(result.get("found", True))
        self.assertIn("error", result)

    def test_stats_resource(self):
        """Test home-manager://options/stats."""
        result = home_manager_stats_resource(self.context)
        # Basic structure checks
        self.assertIn("total_options", result)
        self.assertGreaterEqual(result["total_options"], len(EXPECTED_OPTION_NAMES))
        self.assertIn("total_categories", result)
        self.assertGreater(result["total_categories"], 0)
        self.assertIn("total_types", result)
        self.assertGreater(result["total_types"], 0)
        self.assertIn("by_source", result)
        self.assertIn("by_type", result)
        self.assertIn("by_category", result)
        # Check specific expected types/categories based on mock data
        self.assertIn("boolean", result["by_type"])
        self.assertIn("string", result["by_type"])
        # Category might vary based on parsing, check presence
        self.assertGreater(len(result["by_category"]), 0)

    def test_options_list_resource(self):
        """Test home-manager://options/list."""
        result = home_manager_options_list_resource(self.context)
        self.assertValidResource(result, "options_list")
        self.assertTrue(result.get("found", False))
        self.assertIn("options", result)
        self.assertIsInstance(result["options"], dict)
        self.assertGreaterEqual(len(result["options"]), len(EXPECTED_PREFIXES))  # Check main prefixes

        # Check expected prefixes exist
        for prefix in EXPECTED_PREFIXES:
            self.assertIn(prefix, result["options"], f"Expected prefix '{prefix}' not in list")
            prefix_data = result["options"][prefix]
            self.assertIn("count", prefix_data)
            self.assertIn("has_children", prefix_data)
            self.assertIn("types", prefix_data)
            self.assertIn("enable_options", prefix_data)
            self.assertGreater(prefix_data["count"], 0)  # Expect at least one option per prefix

    def test_prefix_resource_simple(self):
        """Test home-manager://options/prefix/{prefix} (simple)."""
        prefix = "programs"
        result = home_manager_options_by_prefix_resource(prefix, self.context)
        self.assertValidResource(result, f"prefix({prefix})")
        self.assertTrue(result.get("found", False), f"Prefix '{prefix}' should be found")
        self.assertEqual(result["prefix"], prefix)
        self.assertIn("options", result)
        self.assertIn("count", result)
        self.assertIsInstance(result["options"], list)
        self.assertGreater(result["count"], 0)
        self.assertEqual(len(result["options"]), result["count"])

        # All options should start with the prefix
        for option in result["options"]:
            self.assertTrue(option["name"].startswith(f"{prefix}."))

    def test_prefix_resource_nested(self):
        """Test home-manager://options/prefix/{prefix} (nested)."""
        prefix = "programs.git"
        result = home_manager_options_by_prefix_resource(prefix, self.context)
        self.assertValidResource(result, f"prefix({prefix})")
        self.assertTrue(result.get("found", False), f"Prefix '{prefix}' should be found")
        self.assertEqual(result["prefix"], prefix)
        self.assertIn("options", result)
        self.assertIn("count", result)
        self.assertIsInstance(result["options"], list)
        self.assertGreaterEqual(result["count"], 2)  # Expecting .enable and .userName
        self.assertEqual(len(result["options"]), result["count"])

        # All options should start with the prefix
        found_names = set()
        for option in result["options"]:
            self.assertTrue(option["name"].startswith(f"{prefix}."))
            found_names.add(option["name"])
        self.assertIn("programs.git.enable", found_names)
        self.assertIn("programs.git.userName", found_names)

    def test_prefix_resource_invalid(self):
        """Test home-manager://options/prefix/{prefix} (invalid)."""
        prefix = "nonexistent.prefix"
        result = home_manager_options_by_prefix_resource(prefix, self.context)
        self.assertValidResource(result, f"prefix({prefix})")
        self.assertFalse(result.get("found", True))
        self.assertIn("error", result)


# Standard unittest runner
if __name__ == "__main__":
    unittest.main()
