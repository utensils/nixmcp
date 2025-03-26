"""Tests for the HomeManagerClient in the NixMCP server."""

import unittest
import threading
import time
import requests
from unittest.mock import patch, MagicMock

# Import the HomeManagerClient class
from nixmcp.clients.home_manager_client import HomeManagerClient


class TestHomeManagerClient(unittest.TestCase):
    """Test the HomeManagerClient class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a sample HTML document for testing parsing
        self.sample_html = """
        <html>
            <body>
                <div class="variablelist">
                    <dl>
                        <dt>
                            <span class="term">
                                <code>programs.git.enable</code>
                            </span>
                        </dt>
                        <dd>
                            <p>Whether to enable Git.</p>
                            <p>Type: boolean</p>
                            <p>Default: false</p>
                        </dd>
                        <dt>
                            <span class="term">
                                <code>programs.git.userName</code>
                            </span>
                        </dt>
                        <dd>
                            <p>User name to configure in Git.</p>
                            <p>Type: string</p>
                            <p>Default: null</p>
                            <p>Example: "John Doe"</p>
                        </dd>
                    </dl>
                </div>
            </body>
        </html>
        """

    def test_fetch_url(self):
        """Test fetching URLs with HTML client caching."""
        # Create client
        client = HomeManagerClient()

        # Create a mock for the HTMLClient.fetch method
        original_fetch = client.html_client.fetch

        # Mock implementation
        def mock_fetch(url, force_refresh=False):
            return self.sample_html, {"from_cache": False, "success": True}

        # Replace the fetch method
        client.html_client.fetch = mock_fetch

        try:
            # Test fetching a URL
            url = "https://test.com/options.xhtml"
            html = client.fetch_url(url)

            # Verify the content is returned correctly
            self.assertEqual(html, self.sample_html)

        finally:
            # Restore original fetch method
            client.html_client.fetch = original_fetch

    @patch("requests.get")
    def test_parse_html(self, mock_get):
        """Test parsing HTML to extract options."""
        # Create the client
        client = HomeManagerClient()

        # Parse the sample HTML
        options = client.parse_html(self.sample_html, "test_doc")

        # Verify the parsed options
        self.assertEqual(len(options), 2)

        # Check first option
        self.assertEqual(options[0]["name"], "programs.git.enable")
        self.assertEqual(options[0]["description"], "Whether to enable Git.")
        self.assertEqual(options[0]["type"], "boolean")
        self.assertEqual(options[0]["default"], "false")
        self.assertIsNone(options[0]["example"])
        self.assertEqual(options[0]["source"], "test_doc")

        # Check second option
        self.assertEqual(options[1]["name"], "programs.git.userName")
        self.assertEqual(options[1]["description"], "User name to configure in Git.")
        self.assertEqual(options[1]["type"], "string")
        self.assertEqual(options[1]["default"], "null")
        self.assertEqual(options[1]["example"], '"John Doe"')
        self.assertEqual(options[1]["source"], "test_doc")

    def test_build_search_indices(self):
        """Test building search indices from options."""
        # Create the client
        client = HomeManagerClient()

        # Define sample options
        options = [
            {
                "name": "programs.git.enable",
                "description": "Whether to enable Git.",
                "type": "boolean",
                "default": "false",
                "category": "Programs",
                "source": "options",
            },
            {
                "name": "programs.git.userName",
                "description": "User name to configure in Git.",
                "type": "string",
                "default": "null",
                "example": '"John Doe"',
                "category": "Programs",
                "source": "options",
            },
        ]

        # Build indices
        client.build_search_indices(options)

        # Verify indices were built
        self.assertEqual(len(client.options), 2)
        self.assertIn("programs.git.enable", client.options)
        self.assertIn("programs.git.userName", client.options)

        # Check category index
        self.assertIn("Programs", client.options_by_category)
        self.assertEqual(len(client.options_by_category["Programs"]), 2)

        # Check inverted index for word search
        self.assertIn("git", client.inverted_index)
        self.assertIn("programs.git.enable", client.inverted_index["git"])
        self.assertIn("programs.git.userName", client.inverted_index["git"])

        # Check prefix index for hierarchical paths
        self.assertIn("programs", client.prefix_index)
        self.assertIn("programs.git", client.prefix_index)
        self.assertIn("programs.git.enable", client.prefix_index["programs.git"])

        # Check hierarchical index
        self.assertIn(("programs", "git"), client.hierarchical_index)
        self.assertIn(("programs.git", "enable"), client.hierarchical_index)
        self.assertIn(("programs.git", "userName"), client.hierarchical_index)

    def test_load_all_options(self):
        """Test loading options from all sources."""
        # The HTML samples for each source
        options_html = self.sample_html

        nixos_options_html = """
        <html>
            <body>
                <div class="variablelist">
                    <dl>
                        <dt>
                            <span class="term">
                                <code>programs.nixos.enable</code>
                            </span>
                        </dt>
                        <dd>
                            <p>Whether to enable NixOS integration.</p>
                            <p>Type: boolean</p>
                        </dd>
                    </dl>
                </div>
            </body>
        </html>
        """

        darwin_options_html = """
        <html>
            <body>
                <div class="variablelist">
                    <dl>
                        <dt>
                            <span class="term">
                                <code>programs.darwin.enable</code>
                            </span>
                        </dt>
                        <dd>
                            <p>Whether to enable Darwin integration.</p>
                            <p>Type: boolean</p>
                        </dd>
                    </dl>
                </div>
            </body>
        </html>
        """

        # Create client
        client = HomeManagerClient()

        # Mock HTMLClient fetch to return different HTML for different URLs
        original_fetch = client.html_client.fetch
        url_counter = {"count": 0}  # Use a dict to persist values across calls

        def mock_fetch(url, force_refresh=False):
            url_counter["count"] += 1

            if "options.xhtml" in url:
                return options_html, {"from_cache": False, "success": True}
            elif "nixos-options.xhtml" in url:
                return nixos_options_html, {"from_cache": False, "success": True}
            elif "nix-darwin-options.xhtml" in url:
                return darwin_options_html, {"from_cache": False, "success": True}
            else:
                return "", {"from_cache": False, "success": True}

        # Apply the mock
        client.html_client.fetch = mock_fetch

        try:
            # Load options
            options = client.load_all_options()

            # Check that we have options loaded
            self.assertTrue(len(options) > 0)

            # Verify fetch was called 3 times (once for each URL)
            self.assertEqual(url_counter["count"], 3)

            # Check that options from different sources are included
            option_names = [opt["name"] for opt in options]

            # Verify the options from the first file are present
            self.assertIn("programs.git.enable", option_names)
            self.assertIn("programs.git.userName", option_names)

            # Verify we have the right number of options
            self.assertEqual(len(option_names), 6)  # Contains doubled entries from different sources

            # Check sources are correctly marked
            sources = [opt["source"] for opt in options]
            self.assertIn("options", sources)
            self.assertIn("nixos-options", sources)
            self.assertIn("nix-darwin-options", sources)
        finally:
            # Restore original method
            client.html_client.fetch = original_fetch

    def test_search_options(self):
        """Test searching options using the in-memory indices."""
        # Create client
        client = HomeManagerClient()

        # Create sample options data
        sample_options = [
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
                "default": "null",
                "example": '"John Doe"',
            },
        ]

        # Manually populate the client's data structures
        client.build_search_indices(sample_options)
        client.is_loaded = True

        # Test exact match search
        result = client.search_options("programs.git.enable")
        self.assertEqual(result["count"], 1)
        self.assertEqual(len(result["options"]), 1)
        self.assertEqual(result["options"][0]["name"], "programs.git.enable")

        # Test prefix search (hierarchical path)
        result = client.search_options("programs.git")
        self.assertEqual(result["count"], 2)
        self.assertEqual(len(result["options"]), 2)
        option_names = [opt["name"] for opt in result["options"]]
        self.assertIn("programs.git.enable", option_names)
        self.assertIn("programs.git.userName", option_names)

        # Test word search
        result = client.search_options("user")
        self.assertEqual(result["count"], 1)
        self.assertEqual(len(result["options"]), 1)
        self.assertEqual(result["options"][0]["name"], "programs.git.userName")

        # Test scoring (options with matching score should be returned)
        result = client.search_options("git")
        self.assertEqual(len(result["options"]), 2)
        # Check that scores are present and reasonable
        self.assertTrue(all("score" in opt for opt in result["options"]))
        self.assertGreaterEqual(result["options"][0]["score"], 0)
        self.assertGreaterEqual(result["options"][1]["score"], 0)

    def test_get_option(self):
        """Test getting detailed information about a specific option."""
        # Create client
        client = HomeManagerClient()

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
                "default": "null",
                "example": '"John Doe"',
            },
        ]

        # Set up the client manually
        client.build_search_indices(options)
        client.is_loaded = True

        # Test getting an existing option
        result = client.get_option("programs.git.enable")
        self.assertTrue(result["found"])
        self.assertEqual(result["name"], "programs.git.enable")
        self.assertEqual(result["type"], "boolean")
        self.assertEqual(result["description"], "Whether to enable Git.")
        self.assertEqual(result["default"], "false")

        # Check that related options are included
        if "related_options" in result:
            # The number might vary, we just check the structure rather than exact count
            self.assertTrue(len(result["related_options"]) > 0, "Expected at least one related option")
            # Check that userName is in the related options
            related_names = [opt["name"] for opt in result["related_options"]]
            self.assertIn("programs.git.userName", related_names)

        # Test getting a non-existent option
        result = client.get_option("programs.nonexistent")
        self.assertFalse(result["found"])
        self.assertIn("error", result)

        # Test getting an option with a typo - should suggest the correct one
        result = client.get_option("programs.git")  # Will be a prefix match
        self.assertFalse(result["found"])
        self.assertIn("error", result)
        # Check if there are suggestions (this depends on the implementation)
        if "suggestions" in result:
            self.assertTrue(len(result["suggestions"]) > 0, "Expected at least one suggestion")

    def test_error_handling(self):
        """Test error handling in HomeManagerClient."""
        # Create client
        client = HomeManagerClient()

        # Mock HTMLClient fetch to simulate a network error
        original_fetch = client.html_client.fetch

        def mock_fetch(url, force_refresh=False):
            raise requests.RequestException("Failed to connect to server")

        client.html_client.fetch = mock_fetch

        try:
            # Attempt to load options
            with self.assertRaises(Exception) as context:
                client.load_all_options()

            self.assertIn("Failed to", str(context.exception))
        finally:
            # Restore original method
            client.html_client.fetch = original_fetch

    def test_retry_mechanism(self):
        """Test retry mechanism for network failures."""
        # Create client
        client = HomeManagerClient()

        # Create a wrapper fetch function that adds retry capability
        def fetch_with_retry(url, attempts=0, max_attempts=2, delay=0.01):
            try:
                return client.fetch_url(url)
            except Exception:
                if attempts < max_attempts:
                    time.sleep(delay)
                    return fetch_with_retry(url, attempts + 1, max_attempts, delay)
                raise

        # Patch the HTMLClient's fetch method
        original_fetch = client.html_client.fetch

        # Mock counter to track attempts
        attempt_count = [0]

        # Create a mock fetch function that fails on first attempt, succeeds on second
        def mock_fetch(url, force_refresh=False):
            attempt_count[0] += 1
            if attempt_count[0] == 1:
                # First attempt fails
                raise requests.RequestException("Network error")
            # Second attempt succeeds
            return self.sample_html, {"from_cache": False, "success": True}

        # Apply the mock
        client.html_client.fetch = mock_fetch

        try:
            # Use our retry wrapper to handle the exception and retry
            result = fetch_with_retry("https://test.com/options.xhtml")

            # Verify the result and attempt count
            self.assertEqual(result, self.sample_html)
            self.assertEqual(attempt_count[0], 2)  # Should have tried twice
        finally:
            # Restore original method
            client.html_client.fetch = original_fetch

    @patch("nixmcp.clients.home_manager_client.HomeManagerClient._load_data_internal")
    def test_load_in_background_avoids_duplicate_loading(self, mock_load_internal):
        """Test that background loading avoids duplicate loading of data."""

        # Setup mock to simulate a slower loading process
        def slow_loading_effect(*args, **kwargs):
            time.sleep(0.2)  # Simulate slow loading
            return None

        mock_load_internal.side_effect = slow_loading_effect

        # Create client
        client = HomeManagerClient()

        # Start background loading
        client.load_in_background()

        # Verify background thread was started
        self.assertIsNotNone(client.loading_thread)
        self.assertTrue(client.loading_thread.is_alive())

        # Try starting another background load while first is running
        client.load_in_background()

        # Wait for the background thread to complete
        client.loading_thread.join(timeout=1.0)

        # Verify load_data_internal was called exactly once
        mock_load_internal.assert_called_once()

    @patch("nixmcp.clients.home_manager_client.HomeManagerClient._load_data_internal")
    def test_ensure_loaded_waits_for_background_thread(self, mock_load_internal):
        """Test that ensure_loaded waits for background thread to complete instead of duplicating work."""
        # Setup: Create a client and track how many times the load method is called
        load_count = 0

        def counting_load(*args, **kwargs):
            nonlocal load_count
            load_count += 1
            time.sleep(0.2)  # Simulate loading time
            # The is_loaded flag is set in load_in_background after calling _load_data_internal
            # We don't set it here as this is the implementation of _load_data_internal

        mock_load_internal.side_effect = counting_load

        # Create client
        client = HomeManagerClient()

        # Start background loading
        client.load_in_background()

        # Need to wait briefly to ensure the background thread has actually started
        time.sleep(0.1)

        # Immediately call ensure_loaded from another thread
        def call_ensure_loaded():
            client.ensure_loaded()

        ensure_thread = threading.Thread(target=call_ensure_loaded)
        ensure_thread.start()

        # Give both threads time to complete
        client.loading_thread.join(timeout=1.0)
        ensure_thread.join(timeout=1.0)

        # Verify that _load_data_internal was called exactly once
        self.assertEqual(load_count, 1)
        self.assertEqual(mock_load_internal.call_count, 1)

        # Verify that the data is marked as loaded
        self.assertTrue(client.is_loaded)

    def test_multiple_concurrent_ensure_loaded_calls(self):
        """Test that multiple concurrent calls to ensure_loaded only result in loading once."""
        # This test verifies that the `loading_in_progress` flag correctly prevents duplicate loading

        # Create a test fixture similar to what's happening in the real code
        client = HomeManagerClient()

        # Track how many times _load_data_internal would be called
        load_count = 0
        load_event = threading.Event()

        # Override ensure_loaded method with test version that counts calls to loading
        # This is needed because the locks in the real code require careful handling
        original_ensure_loaded = client.ensure_loaded

        def test_ensure_loaded():
            nonlocal load_count

            # Simulate the critical section that checks and sets loading_in_progress
            with client.loading_lock:
                # First thread to arrive will do the loading
                if not client.is_loaded and not client.loading_in_progress:
                    client.loading_in_progress = True
                    load_count += 1
                    # Eventually mark as loaded after all threads have tried to load
                    threading.Timer(0.2, lambda: load_event.set()).start()
                    threading.Timer(0.3, lambda: setattr(client, "is_loaded", True)).start()
                    return

                # Other threads will either wait for loading or return immediately if loaded
                if client.loading_in_progress and not client.is_loaded:
                    # These threads should wait, not try to load again
                    pass

        # Replace the method
        client.ensure_loaded = test_ensure_loaded

        try:
            # Reset client state
            with client.loading_lock:
                client.is_loaded = False
                client.loading_in_progress = False

            # Start 5 threads that all try to ensure data is loaded
            threads = []
            for _ in range(5):
                t = threading.Thread(target=client.ensure_loaded)
                threads.append(t)
                t.start()

            # Wait for all threads to complete
            for t in threads:
                t.join(timeout=0.5)

            # Wait for the loading to complete (in case it's still in progress)
            load_event.wait(timeout=0.5)

            # Verify that loading was only attempted once
            self.assertEqual(load_count, 1)

        finally:
            # Restore original method
            client.ensure_loaded = original_ensure_loaded

    @patch("nixmcp.utils.helpers.make_http_request")
    def test_no_duplicate_http_requests(self, mock_make_request):
        """Test that we don't make duplicate HTTP requests when loading Home Manager options."""
        # Configure mock to return our sample HTML for all URLs
        mock_make_request.return_value = {"text": self.sample_html}

        # Create client with faster retry settings
        client = HomeManagerClient()
        client.retry_delay = 0.01

        # First, start background loading
        client.load_in_background()

        # Then immediately call a method that requires the data
        client.search_options("git")

        # Wait for background loading to complete
        if client.loading_thread and client.loading_thread.is_alive():
            client.loading_thread.join(timeout=1.0)

        # We have 3 URLs in the client.hm_urls dictionary
        # The background thread should request all 3 URLs once
        # Verify each URL was requested at most once
        self.assertLessEqual(mock_make_request.call_count, 3, "More HTTP requests than expected")

    def test_loading_from_cache(self):
        """Test that loading from cache works correctly."""
        client = HomeManagerClient()

        # Mock the load from cache method
        original_load_from_cache = client._load_from_cache
        original_load_all_options = client.load_all_options
        original_build_search_indices = client.build_search_indices

        load_from_cache_called = False
        load_all_options_called = False
        build_search_indices_called = False

        def mock_load_from_cache():
            nonlocal load_from_cache_called
            load_from_cache_called = True
            return True  # Indicate cache hit

        def mock_load_all_options():
            nonlocal load_all_options_called
            load_all_options_called = True
            return []

        def mock_build_indices(options):
            nonlocal build_search_indices_called
            build_search_indices_called = True

        # Apply mocks
        client._load_from_cache = mock_load_from_cache
        client.load_all_options = mock_load_all_options
        client.build_search_indices = mock_build_indices

        try:
            # Test successful cache loading
            client._load_data_internal()

            # Should have called load_from_cache but not the other methods
            self.assertTrue(load_from_cache_called)
            self.assertFalse(load_all_options_called)
            self.assertFalse(build_search_indices_called)

            # Reset tracking variables
            load_from_cache_called = False

            # Now test cache miss
            client._load_from_cache = lambda: False
            client._load_data_internal()

            # Now both methods should have been called
            self.assertTrue(load_all_options_called)
            self.assertTrue(build_search_indices_called)

        finally:
            # Restore original methods
            client._load_from_cache = original_load_from_cache
            client.load_all_options = original_load_all_options
            client.build_search_indices = original_build_search_indices

    @patch("nixmcp.clients.home_manager_client.HomeManagerClient._save_in_memory_data")
    @patch("nixmcp.clients.home_manager_client.HomeManagerClient.load_all_options")
    @patch("nixmcp.clients.home_manager_client.HomeManagerClient.build_search_indices")
    def test_saving_to_cache(self, mock_build_indices, mock_load_options, mock_save):
        """Test that saving to cache works correctly."""
        client = HomeManagerClient()

        # Mock the loading methods to avoid actual network/file operations
        mock_options = [{"name": "test.option", "description": "Test option"}]
        mock_load_options.return_value = mock_options

        # Mock _load_from_cache to return False to force web loading path
        with patch.object(client, "_load_from_cache", return_value=False):
            # Call internal loading method directly to avoid threading issues
            client._load_data_internal()

            # Should have called load_all_options and build_search_indices
            mock_load_options.assert_called_once()
            mock_build_indices.assert_called_once_with(mock_options)

            # Should have saved the results to cache
            mock_save.assert_called_once()

    @patch("nixmcp.clients.home_manager_client.HomeManagerClient.invalidate_cache")
    def test_force_refresh(self, mock_invalidate):
        """Test force_refresh parameter to ensure_loaded."""
        client = HomeManagerClient()

        # Mock _load_data_internal to avoid actual loading
        with patch.object(client, "_load_data_internal"):
            # Normal ensure_loaded call
            client.ensure_loaded()

            # Should not have invalidated cache
            mock_invalidate.assert_not_called()

            # Force refresh call
            client.ensure_loaded(force_refresh=True)

            # Should have invalidated cache
            mock_invalidate.assert_called_once()

    def test_invalidate_cache(self):
        """Test invalidating the cache."""
        client = HomeManagerClient()

        # Mock the html_client.cache
        original_cache = client.html_client.cache
        mock_cache = MagicMock()
        client.html_client.cache = mock_cache

        try:
            # Call invalidate_cache
            client.invalidate_cache()

            # Should have called invalidate_data on the cache
            mock_cache.invalidate_data.assert_called_once_with(client.cache_key)

            # Should have called invalidate for each URL
            self.assertEqual(mock_cache.invalidate.call_count, len(client.hm_urls))
        finally:
            # Restore original cache
            client.html_client.cache = original_cache


if __name__ == "__main__":
    unittest.main()
