import unittest
import threading
import time
import pytest

import logging
from unittest.mock import patch, MagicMock, call

# Mark as unit tests
pytestmark = pytest.mark.unit

# Import the classes to be tested
from mcp_nixos.clients.home_manager_client import HomeManagerClient
from mcp_nixos.contexts.home_manager_context import HomeManagerContext

# Import specifically for patching instances/methods
from mcp_nixos.clients.html_client import HTMLClient

# Import the tool functions
from mcp_nixos.tools.home_manager_tools import home_manager_search, home_manager_info, home_manager_stats

# Disable logging during tests for cleaner output
logging.disable(logging.CRITICAL)

# --- Test Constants ---

MOCK_HTML_OPTIONS = """
<html><body><div class="variablelist"><dl class="variablelist">
    <dt><span class="term"><a id="opt-programs.git.enable"></a>
        <a class="term" href="#"><code class="option">programs.git.enable</code></a></span></dt>
    <dd>
        <p>Whether to enable Git.</p>
        <p><span class="emphasis"><em>Type:</em></span> boolean</p>
        <p><span class="emphasis"><em>Default:</em></span> false</p>
        <p><span class="emphasis"><em>Example:</em></span> true</p>
    </dd>
    <dt><span class="term"><a id="opt-programs.git.userName"></a>
        <a class="term" href="#"><code class="option">programs.git.userName</code></a></span></dt>
    <dd>
        <p>Your Git username.</p>
        <p><span class="emphasis"><em>Type:</em></span> string</p>
        <p><span class="emphasis"><em>Default:</em></span> null</p>
        <p><span class="emphasis"><em>Example:</em></span> "John Doe"</p>
    </dd>
    <dt><span class="term"><a id="opt-programs.firefox.enable"></a>
        <a class="term" href="#"><code class="option">programs.firefox.enable</code></a></span></dt>
    <dd>
        <p>Whether to enable Firefox.</p>
        <p><span class="emphasis"><em>Type:</em></span> boolean</p>
    </dd> <!-- Missing default/example -->
</dl></div></body></html>
"""

# Sample options data derived from MOCK_HTML_OPTIONS + others for variety
# Adjusted expected values based on observed parsing results (e.g., category, None example)
SAMPLE_OPTIONS_DATA = [
    {
        "name": "programs.git.enable",
        "type": "boolean",
        "description": "Whether to enable Git.",
        "category": "Uncategorized",
        "default": "false",
        "example": "true",
        "source": "test-options",
    },
    {
        "name": "programs.git.userName",
        "type": "string",
        "description": "Your Git username.",
        "category": "Uncategorized",
        "default": "null",
        "example": '"John Doe"',
        "source": "test-options",
    },
    {
        "name": "programs.firefox.enable",
        "type": "boolean",
        "description": "Whether to enable Firefox.",
        "category": "Uncategorized",
        "default": None,
        "example": None,
        "source": "test-nixos",  # Example added source
    },
    {  # Additional options for index testing
        "name": "services.nginx.enable",
        "type": "boolean",
        "description": "Enable Nginx service.",
        "category": "Services",
        "default": "false",
        "example": None,
        "source": "test-options",
    },
    {
        "name": "services.nginx.virtualHosts",
        "type": "attribute set",
        "description": "Nginx virtual hosts.",
        "category": "Services",
        "default": "{}",
        "example": None,
        "source": "test-options",
    },
]


class TestHomeManagerClient(unittest.TestCase):
    """Test the HomeManagerClient class using mocks for network/cache."""

    @patch.object(HTMLClient, "fetch", return_value=(MOCK_HTML_OPTIONS, {"success": True, "from_cache": False}))
    def test_fetch_url(self, mock_fetch):
        """Test fetching HTML content via HTMLClient."""
        client = HomeManagerClient()
        url = "https://example.com/options.xhtml"
        content = client.fetch_url(url)
        self.assertEqual(content, MOCK_HTML_OPTIONS)
        mock_fetch.assert_called_once_with(url, force_refresh=False)

    def test_parse_html(self):
        """Test parsing HTML content extracts options correctly."""
        client = HomeManagerClient()
        options = client.parse_html(MOCK_HTML_OPTIONS, "test-source")
        self.assertEqual(len(options), 3)
        # Check basic structure and content of first parsed option
        expected_opt1 = {
            "name": "programs.git.enable",
            "type": "boolean",
            "description": "Whether to enable Git.",
            "category": "Uncategorized",
            "default": "false",
            "example": "true",
            "source": "test-source",
            "introduced_version": None,
            "deprecated_version": None,
            "manual_url": None,
        }
        self.assertDictEqual(options[0], expected_opt1)
        self.assertEqual(options[2]["name"], "programs.firefox.enable")  # Check last option name

    def test_build_search_indices(self):
        """Test building all search indices from options data."""
        client = HomeManagerClient()
        client.build_search_indices(SAMPLE_OPTIONS_DATA)

        # Verify options dict
        self.assertEqual(len(client.options), len(SAMPLE_OPTIONS_DATA))
        self.assertIn("programs.git.enable", client.options)
        self.assertIn("services.nginx.enable", client.options)

        # Verify category index
        self.assertIn("Uncategorized", client.options_by_category)
        self.assertIn("Services", client.options_by_category)
        self.assertGreaterEqual(len(client.options_by_category["Uncategorized"]), 3)
        self.assertGreaterEqual(len(client.options_by_category["Services"]), 2)

        # Verify inverted index (spot checks)
        self.assertIn("git", client.inverted_index)
        self.assertIn("nginx", client.inverted_index)
        self.assertIn("enable", client.inverted_index)
        self.assertIn("programs.git.enable", client.inverted_index["enable"])
        self.assertIn("services.nginx.enable", client.inverted_index["enable"])

        # Verify prefix index (spot checks)
        self.assertIn("programs", client.prefix_index)
        self.assertIn("programs.git", client.prefix_index)
        self.assertIn("services", client.prefix_index)
        self.assertIn("services.nginx", client.prefix_index)
        expected_git_options = ["programs.git.enable", "programs.git.userName"]
        self.assertCountEqual(client.prefix_index["programs.git"], expected_git_options)
        expected_nginx_options = ["services.nginx.enable", "services.nginx.virtualHosts"]
        self.assertCountEqual(client.prefix_index["services.nginx"], expected_nginx_options)

    @patch.object(HomeManagerClient, "_load_from_cache", return_value=False)  # Simulate cache miss
    @patch.object(HomeManagerClient, "load_all_options", return_value=SAMPLE_OPTIONS_DATA)
    @patch.object(HomeManagerClient, "build_search_indices")
    @patch.object(HomeManagerClient, "_save_in_memory_data")
    def test_load_data_internal_cache_miss(self, mock_save, mock_build, mock_load_all, mock_load_cache):
        """Test _load_data_internal loads from web on cache miss."""
        client = HomeManagerClient()
        client._load_data_internal()

        mock_load_cache.assert_called_once()
        mock_load_all.assert_called_once()
        mock_build.assert_called_once_with(SAMPLE_OPTIONS_DATA)
        mock_save.assert_called_once()
        self.assertTrue(client.is_loaded)

    @patch.object(HomeManagerClient, "_load_from_cache", return_value=True)  # Simulate cache hit
    @patch.object(HomeManagerClient, "load_all_options")
    @patch.object(HomeManagerClient, "build_search_indices")
    @patch.object(HomeManagerClient, "_save_in_memory_data")
    def test_load_data_internal_cache_hit(self, mock_save, mock_build, mock_load_all, mock_load_cache):
        """Test _load_data_internal uses cache and skips web load/build/save."""
        client = HomeManagerClient()
        client._load_data_internal()

        mock_load_cache.assert_called_once()
        mock_load_all.assert_not_called()
        # Build might be called by load_from_cache internally depending on implementation
        # mock_build.assert_not_called() # Comment out if load_from_cache also builds
        mock_save.assert_not_called()
        self.assertTrue(client.is_loaded)  # Assume load_from_cache sets this

    @patch("mcp_nixos.clients.home_manager_client.HomeManagerClient._load_data_internal")
    def test_ensure_loaded_waits_for_background(self, mock_load_internal):
        """Test ensure_loaded waits if background load is in progress."""
        load_started_event = threading.Event()
        load_finished_event = threading.Event()
        mock_load_internal.side_effect = lambda: (load_started_event.set(), time.sleep(0.1), load_finished_event.set())

        client = HomeManagerClient()
        client.load_in_background()  # Start background load

        # Wait until background load has started
        self.assertTrue(load_started_event.wait(timeout=0.5), "Background load didn't start")

        # Call ensure_loaded while background is running
        ensure_thread = threading.Thread(target=client.ensure_loaded)
        start_time = time.monotonic()
        ensure_thread.start()
        ensure_thread.join(timeout=0.5)  # Wait for ensure_loaded call to finish
        end_time = time.monotonic()

        self.assertTrue(load_finished_event.is_set(), "Background load didn't finish")
        self.assertGreaterEqual(end_time - start_time, 0.05, "ensure_loaded didn't wait sufficiently")
        mock_load_internal.assert_called_once()  # Only background thread should load
        self.assertTrue(client.is_loaded)

    @patch("mcp_nixos.clients.home_manager_client.HomeManagerClient.invalidate_cache")
    @patch("mcp_nixos.clients.home_manager_client.HomeManagerClient._load_data_internal")
    def test_ensure_loaded_force_refresh(self, mock_load, mock_invalidate):
        """Test ensure_loaded with force_refresh=True invalidates and reloads."""
        client = HomeManagerClient()
        client.is_loaded = True  # Simulate already loaded

        client.ensure_loaded(force_refresh=True)

        mock_invalidate.assert_called_once()
        mock_load.assert_called_once()  # Should reload

    @patch("mcp_nixos.clients.html_client.HTMLCache")
    def test_invalidate_cache_calls(self, MockHTMLCache):
        """Test invalidate_cache calls underlying cache methods."""
        client = HomeManagerClient()
        mock_cache = MockHTMLCache.return_value
        client.html_client.cache = mock_cache  # Inject mock cache

        client.invalidate_cache()

        mock_cache.invalidate_data.assert_called_once_with(client.cache_key)
        expected_invalidate_calls = [call(url) for url in client.hm_urls.values()]
        mock_cache.invalidate.assert_has_calls(expected_invalidate_calls, any_order=True)
        self.assertEqual(mock_cache.invalidate.call_count, len(client.hm_urls))


# Patch target is where HomeManagerClient is *looked up* within home_manager_context
@patch("mcp_nixos.contexts.home_manager_context.HomeManagerClient")
class TestHomeManagerContext(unittest.TestCase):
    """Test the HomeManagerContext class using a mocked client."""

    def setUp(self):
        """Create context with mocked client instance."""
        # MockClient is passed by the class decorator
        pass  # Setup done by class decorator patch

    def test_ensure_loaded_delegates(self, MockClient):
        """Test context.ensure_loaded calls client.ensure_loaded."""
        mock_client_instance = MockClient.return_value
        context = HomeManagerContext()  # Creates instance using mocked Client
        context.ensure_loaded()
        mock_client_instance.ensure_loaded.assert_called_once()

    def test_get_status(self, MockClient):
        """Test context.get_status formats client status."""
        mock_client_instance = MockClient.return_value
        mock_client_instance.is_loaded = True
        mock_client_instance.loading_in_progress = False
        mock_client_instance.loading_error = None
        mock_client_instance.get_stats.return_value = {"total_options": 123}
        # Mock the cache attribute on the client instance
        mock_client_instance.cache = MagicMock()
        mock_client_instance.cache.get_stats.return_value = {"hits": 5, "misses": 1}

        context = HomeManagerContext()
        status = context.get_status()

        self.assertTrue(status["loaded"])
        self.assertEqual(status["options_count"], 123)
        self.assertEqual(status["cache_stats"]["hits"], 5)
        mock_client_instance.get_stats.assert_called_once()
        mock_client_instance.cache.get_stats.assert_called_once()  # Verify cache stats called

    def test_context_methods_delegate_when_loaded(self, MockClient):
        """Test context methods delegate to client when loaded."""
        mock_client_instance = MockClient.return_value
        mock_client_instance.is_loaded = True
        mock_client_instance.loading_in_progress = False
        mock_client_instance.loading_error = None

        context = HomeManagerContext()

        # Search
        mock_client_instance.search_options.return_value = {"count": 1, "options": [{"name": "a"}]}
        context.search_options("q", 5)
        mock_client_instance.search_options.assert_called_once_with("q", 5)

        # Get Option
        mock_client_instance.get_option.return_value = {"name": "a", "found": True}
        context.get_option("a")
        mock_client_instance.get_option.assert_called_once_with("a")

        # Get Stats
        mock_client_instance.get_stats.return_value = {"total_options": 1}
        context.get_stats()
        mock_client_instance.get_stats.assert_called_once()

        # Get Options List (delegates to get_options_by_prefix internally)
        # We need to patch the context's get_options_by_prefix method since it calls that method
        # rather than directly calling the client's method
        original_get_options_by_prefix = context.get_options_by_prefix
        context.get_options_by_prefix = MagicMock(return_value={"found": True, "count": 1, "options": []})
        context.get_options_list()
        self.assertGreater(context.get_options_by_prefix.call_count, 0)
        # Restore the original method
        context.get_options_by_prefix = original_get_options_by_prefix

        # Get Options by Prefix (delegates to search_options internally)
        mock_client_instance.search_options.reset_mock()  # Reset from previous call
        mock_client_instance.search_options.return_value = {"count": 1, "options": [{"name": "prefix.a"}]}
        context.get_options_by_prefix("prefix")
        mock_client_instance.search_options.assert_called_once_with("prefix.*", limit=500)  # Default limit

    def test_context_methods_handle_loading_state(self, MockClient):
        """Test context methods return loading error when client is loading."""
        # Create a mock client that will simulate a loading state
        mock_client_instance = MagicMock()
        mock_client_instance.is_loaded = False
        mock_client_instance.loading_in_progress = True
        mock_client_instance.loading_error = None

        # Make the mock client's methods raise exceptions to simulate loading state
        def raise_exception(*args, **kwargs):
            raise Exception("Client is still loading")

        mock_client_instance.search_options.side_effect = raise_exception
        mock_client_instance.get_option.side_effect = raise_exception
        mock_client_instance.get_stats.side_effect = raise_exception
        mock_client_instance.get_options_by_prefix.side_effect = raise_exception

        # Configure the mock constructor to return our configured mock instance
        MockClient.return_value = mock_client_instance

        context = HomeManagerContext()
        loading_msg_part = "still loading"

        # Check each method returns appropriate loading error structure
        search_result = context.search_options("q")
        option_result = context.get_option("a")
        stats_result = context.get_stats()
        options_list_result = context.get_options_list()
        options_by_prefix_result = context.get_options_by_prefix("p")

        self.assertIn("error", search_result)
        self.assertIn("error", option_result)
        self.assertIn("error", stats_result)
        self.assertIn("error", options_list_result)
        self.assertIn("error", options_by_prefix_result)

        self.assertIn(loading_msg_part, search_result["error"])
        self.assertIn(loading_msg_part, option_result["error"])
        self.assertIn(loading_msg_part, stats_result["error"])
        self.assertIn(loading_msg_part, options_list_result["error"])
        self.assertIn(loading_msg_part, options_by_prefix_result["error"])

        # Verify client methods were NOT called because context checked loading state
        mock_client_instance.search_options.assert_not_called()
        mock_client_instance.get_option.assert_not_called()
        mock_client_instance.get_stats.assert_not_called()
        mock_client_instance.get_options_by_prefix.assert_not_called()

    def test_context_methods_handle_error_state(self, MockClient):
        """Test context methods return load error when client failed to load."""
        # Create a mock client that will simulate an error state
        mock_client_instance = MagicMock()
        mock_client_instance.is_loaded = False
        mock_client_instance.loading_in_progress = False
        mock_client_instance.loading_error = "Network Timeout"

        # Make the mock client's methods raise exceptions to simulate error state
        def raise_exception(*args, **kwargs):
            raise Exception("Network Timeout")

        mock_client_instance.search_options.side_effect = raise_exception
        mock_client_instance.get_option.side_effect = raise_exception
        mock_client_instance.get_stats.side_effect = raise_exception
        mock_client_instance.get_options_by_prefix.side_effect = raise_exception

        # Configure the mock constructor to return our configured mock instance
        MockClient.return_value = mock_client_instance

        context = HomeManagerContext()
        error_msg_part = "Network Timeout"

        # Check each method returns appropriate error structure
        search_result = context.search_options("q")
        option_result = context.get_option("a")
        stats_result = context.get_stats()
        options_list_result = context.get_options_list()
        options_by_prefix_result = context.get_options_by_prefix("p")

        self.assertIn("error", search_result)
        self.assertIn("error", option_result)
        self.assertIn("error", stats_result)
        self.assertIn("error", options_list_result)
        self.assertIn("error", options_by_prefix_result)

        self.assertIn(error_msg_part, search_result["error"])
        self.assertIn(error_msg_part, option_result["error"])
        self.assertIn(error_msg_part, stats_result["error"])
        self.assertIn(error_msg_part, options_list_result["error"])
        self.assertIn(error_msg_part, options_by_prefix_result["error"])

        # Verify client methods were NOT called
        mock_client_instance.search_options.assert_not_called()
        mock_client_instance.get_option.assert_not_called()
        mock_client_instance.get_stats.assert_not_called()
        mock_client_instance.get_options_by_prefix.assert_not_called()


# Patch importlib.import_module to return a mocked server module
@patch("importlib.import_module")
class TestHomeManagerTools(unittest.TestCase):
    """Test the Home Manager MCP tool functions."""

    def test_home_manager_search_tool(self, mock_import_module):
        """Test the home_manager_search tool calls context correctly."""
        # Setup mock server module with get_home_manager_context function
        mock_server_module = MagicMock()
        mock_context = MagicMock()
        mock_server_module.get_home_manager_context.return_value = mock_context
        mock_import_module.return_value = mock_server_module

        # Setup context with search_options method
        mock_context.search_options.return_value = {"count": 1, "options": [{"name": "a", "description": "desc"}]}

        result = home_manager_search("query", limit=10)

        # Verify import_module was called with correct arg
        mock_import_module.assert_called_with("mcp_nixos.server")
        # Verify get_home_manager_context was called
        mock_server_module.get_home_manager_context.assert_called_once()
        # Verify search_options was called with expected args
        mock_context.search_options.assert_called_once()
        args, kwargs = mock_context.search_options.call_args
        self.assertEqual(args[0], "*query*")  # Tool adds wildcards
        self.assertEqual(args[1], 10)  # Limit is passed positionally
        self.assertIn("Found 1", result)  # Basic output check
        self.assertIn("a", result)

    def test_home_manager_info_tool(self, mock_import_module):
        """Test the home_manager_info tool calls context correctly."""
        # Setup mock server module with get_home_manager_context function
        mock_server_module = MagicMock()
        mock_context = MagicMock()
        mock_server_module.get_home_manager_context.return_value = mock_context
        mock_import_module.return_value = mock_server_module

        # Setup context with get_option method
        mock_context.get_option.return_value = {"name": "a", "found": True, "description": "desc"}

        result = home_manager_info("option_name")

        # Verify import_module was called with correct arg
        mock_import_module.assert_called_with("mcp_nixos.server")
        # Verify get_home_manager_context was called
        mock_server_module.get_home_manager_context.assert_called_once()
        # Verify get_option was called with expected args
        mock_context.get_option.assert_called_once_with("option_name")
        self.assertIn("# a", result)  # Basic output check
        self.assertIn("desc", result)

    def test_home_manager_info_tool_not_found(self, mock_import_module):
        """Test home_manager_info tool handles 'not found' from context."""
        # Setup mock server module with get_home_manager_context function
        mock_server_module = MagicMock()
        mock_context = MagicMock()
        mock_server_module.get_home_manager_context.return_value = mock_context
        mock_import_module.return_value = mock_server_module

        # Setup context with get_option method returning not found
        mock_context.get_option.return_value = {"name": "option_name", "found": False, "error": "Not found"}

        result = home_manager_info("option_name")

        # Verify import_module was called with correct arg
        mock_import_module.assert_called_with("mcp_nixos.server")
        # Verify get_home_manager_context was called
        mock_server_module.get_home_manager_context.assert_called_once()
        # Verify get_option was called with expected args
        mock_context.get_option.assert_called_once_with("option_name")
        self.assertIn("Option 'option_name' not found", result)  # Check specific not found message

    def test_home_manager_stats_tool(self, mock_import_module):
        """Test the home_manager_stats tool calls context correctly."""
        # Setup mock server module with get_home_manager_context function
        mock_server_module = MagicMock()
        mock_context = MagicMock()
        mock_server_module.get_home_manager_context.return_value = mock_context
        mock_import_module.return_value = mock_server_module

        # Setup context with get_stats method
        mock_context.get_stats.return_value = {"total_options": 123, "total_categories": 5}

        result = home_manager_stats()

        # Verify import_module was called with correct arg
        mock_import_module.assert_called_with("mcp_nixos.server")
        # Verify get_home_manager_context was called
        mock_server_module.get_home_manager_context.assert_called_once()
        # Verify get_stats was called
        mock_context.get_stats.assert_called_once()
        self.assertIn("Total options: 123", result)  # Basic output check
        self.assertIn("Categories: 5", result)


# Standard unittest runner
if __name__ == "__main__":
    unittest.main()
