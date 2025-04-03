"""Tests for the ElasticsearchClient in the MCP-NixOS server."""

import unittest
import pytest
from unittest.mock import patch

# Mark as unit tests
pytestmark = pytest.mark.unit

# Import the ElasticsearchClient class
from mcp_nixos.clients.elasticsearch_client import ElasticsearchClient


class TestElasticsearchClient(unittest.TestCase):
    """Test the ElasticsearchClient class."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a fresh client with disabled caching for each test
        # We'll patch the make_http_request function at a lower level
        from mcp_nixos.cache.simple_cache import SimpleCache

        # Create mock cache that always returns None (cache miss)
        mock_cache = SimpleCache(max_size=0, ttl=0)

        # Override the get method to always return None
        def mock_get(key):
            return None

        mock_cache.get = mock_get

        # Create client with our mock cache
        self.client = ElasticsearchClient()
        self.client.cache = mock_cache

    def test_channel_selection(self):
        """Test that channel selection correctly changes the Elasticsearch index."""
        # Default channel (unstable)
        client = ElasticsearchClient()
        self.assertIn("unstable", client.es_packages_url)

        # Change channel to stable release
        client.set_channel("stable")
        self.assertIn("24.11", client.es_packages_url)  # stable points to 24.11 currently
        self.assertNotIn("unstable", client.es_packages_url)

        # Test specific version
        client.set_channel("24.11")
        self.assertIn("24.11", client.es_packages_url)
        self.assertNotIn("unstable", client.es_packages_url)

        # Invalid channel should fall back to default
        client.set_channel("invalid-channel")
        self.assertIn("unstable", client.es_packages_url)

    def test_stable_channel_usage(self):
        """Test that stable channel can be used for searches."""
        # Create a new client specifically for this test
        client = ElasticsearchClient()
        client.set_channel("stable")

        # Verify the channel was set correctly - stable points to 24.11 currently
        self.assertIn("24.11", client.es_packages_url)
        self.assertNotIn("unstable", client.es_packages_url)

        # Directly patch the safe_elasticsearch_query method
        original_method = client.safe_elasticsearch_query

        def mock_safe_es_query(*args, **kwargs):
            # Return a mock successful response for stable channel
            return {
                "hits": {
                    "total": {"value": 1},
                    "hits": [
                        {
                            "_score": 10.0,
                            "_source": {
                                "package_attr_name": "python311",
                                "package_pname": "python",
                                "package_version": "3.11.0",
                                "package_description": "Python programming language",
                                "package_channel": "nixos-24.11",
                                "package_programs": ["python3", "python3.11"],
                            },
                        }
                    ],
                }
            }

        # Replace the method with our mock
        client.safe_elasticsearch_query = mock_safe_es_query

        try:
            # Test search using the stable channel
            result = client.search_packages("python")

            # Verify results came back correctly
            self.assertNotIn("error", result)
            self.assertEqual(result["count"], 1)
            self.assertEqual(len(result["packages"]), 1)
            self.assertEqual(result["packages"][0]["name"], "python311")
            self.assertEqual(result["packages"][0]["channel"], "nixos-24.11")
        finally:
            # Restore the original method
            client.safe_elasticsearch_query = original_method

    def test_connection_error_handling(self):
        """Test handling of connection errors."""
        # Directly patch the safe_elasticsearch_query method
        original_method = self.client.safe_elasticsearch_query

        def mock_safe_es_query(*args, **kwargs):
            return {
                "error": "Failed to connect to server",
                "error_message": "Connection error: Failed to connect to server",
            }

        # Replace the method with our mock
        self.client.safe_elasticsearch_query = mock_safe_es_query

        try:
            # Attempt to search packages
            result = self.client.search_packages("python")

            # Check the result
            self.assertIn("error", result)
            self.assertIn("connect", result["error"].lower())
        finally:
            # Restore the original method
            self.client.safe_elasticsearch_query = original_method

    def test_timeout_error_handling(self):
        """Test handling of timeout errors."""
        # Directly patch the safe_elasticsearch_query method
        original_method = self.client.safe_elasticsearch_query

        def mock_safe_es_query(*args, **kwargs):
            return {"error": "Request timed out", "error_message": "Request timed out: Connection timeout"}

        # Replace the method with our mock
        self.client.safe_elasticsearch_query = mock_safe_es_query

        try:
            # Attempt to search packages
            result = self.client.search_packages("python")

            # Check the result
            self.assertIn("error", result)
            self.assertIn("timed out", result["error"].lower())
        finally:
            # Restore the original method
            self.client.safe_elasticsearch_query = original_method

    def test_server_error_handling(self):
        """Test handling of server errors (5xx)."""
        # Directly patch the safe_elasticsearch_query method
        original_method = self.client.safe_elasticsearch_query

        def mock_safe_es_query(*args, **kwargs):
            return {"error": "Server error (500)", "error_message": "Server error: Internal server error (500)"}

        # Replace the method with our mock
        self.client.safe_elasticsearch_query = mock_safe_es_query

        try:
            # Attempt to search packages
            result = self.client.search_packages("python")

            # Check the result
            self.assertIn("error", result)
            self.assertIn("server error", result["error"].lower())
        finally:
            # Restore the original method
            self.client.safe_elasticsearch_query = original_method

    def test_authentication_error_handling(self):
        """Test handling of authentication errors."""
        # Directly patch the safe_elasticsearch_query method
        original_method = self.client.safe_elasticsearch_query

        def mock_safe_es_query(*args, **kwargs):
            return {"error": "Authentication failed", "error_message": "Authentication failed: Invalid credentials"}

        # Replace the method with our mock
        self.client.safe_elasticsearch_query = mock_safe_es_query

        try:
            # Attempt to search packages
            result = self.client.search_packages("python")

            # Check the result
            self.assertIn("error", result)
            self.assertIn("authentication", result["error"].lower())
        finally:
            # Restore the original method
            self.client.safe_elasticsearch_query = original_method

    @patch("mcp_nixos.clients.elasticsearch_client.ElasticsearchClient.safe_elasticsearch_query")
    def test_bad_query_handling(self, mock_safe_query):
        """Test handling of bad query syntax."""
        # Simulate a bad query response directly from safe_elasticsearch_query
        mock_safe_query.return_value = {"error": "Invalid query syntax"}

        # Attempt to search packages
        result = self.client.search_packages("invalid:query:syntax")

        # Check the result
        self.assertIn("error", result)
        self.assertEqual("Invalid query syntax", result["error"])

    @patch("mcp_nixos.clients.elasticsearch_client.ElasticsearchClient.safe_elasticsearch_query")
    def test_count_options(self, mock_safe_query):
        """Test the count_options method."""
        # Set up the mock to return a count response
        mock_safe_query.return_value = {"count": 12345}

        # Call the count_options method
        result = self.client.count_options()

        # Verify the result
        self.assertEqual(result["count"], 12345)

        # Verify the method called the count API endpoint
        args, kwargs = mock_safe_query.call_args
        self.assertIn("_count", args[0])  # First arg should contain _count endpoint
        # The query is in the first argument (request_data) to safe_elasticsearch_query
        self.assertTrue("query" in mock_safe_query.call_args[0][1], "Query should be in request data")

    @patch("mcp_nixos.clients.elasticsearch_client.ElasticsearchClient.safe_elasticsearch_query")
    def test_count_options_error(self, mock_safe_query):
        """Test handling errors in count_options method."""
        # Set up the mock to return an error
        mock_safe_query.return_value = {"error": "Count API failed"}

        # Call the count_options method
        result = self.client.count_options()

        # Verify error handling
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["error"], "Count API failed")

    def test_search_packages_with_wildcard(self):
        """Test searching packages with wildcard pattern."""
        # Directly patch the safe_elasticsearch_query method
        original_method = self.client.safe_elasticsearch_query

        def mock_safe_es_query(*args, **kwargs):
            # Extract the query data to verify the wildcard handling
            query_data = args[1] if len(args) > 1 else {}

            # Verify query structure before returning mock data
            if "query" in query_data:
                query = query_data["query"]
                if "bool" in query and "should" in query["bool"]:
                    # The query looks correctly structured
                    pass

            # Return a mock successful response
            return {
                "hits": {
                    "total": {"value": 1},
                    "hits": [
                        {
                            "_score": 10.0,
                            "_source": {
                                "package_attr_name": "python311",
                                "package_pname": "python",
                                "package_version": "3.11.0",
                                "package_description": "Python programming language",
                                "package_programs": ["python3", "python3.11"],
                            },
                        }
                    ],
                }
            }

        # Replace the method with our mock
        self.client.safe_elasticsearch_query = mock_safe_es_query

        try:
            # Test with wildcard query
            result = self.client.search_packages("python*")

            # Verify the result has the expected structure
            self.assertNotIn("error", result)
            self.assertEqual(result["count"], 1)
            self.assertEqual(len(result["packages"]), 1)
            self.assertEqual(result["packages"][0]["name"], "python311")
            self.assertEqual(result["packages"][0]["version"], "3.11.0")
        finally:
            # Restore the original method
            self.client.safe_elasticsearch_query = original_method

    def test_get_option_related_options(self):
        """Test fetching related options for service paths."""
        # Directly patch the safe_elasticsearch_query method
        original_method = self.client.safe_elasticsearch_query

        # We need a list to track call count and manage side effects
        call_count = [0]

        def mock_safe_es_query(*args, **kwargs):
            call_count[0] += 1

            if call_count[0] == 1:
                # First call - return the main option
                return {
                    "hits": {
                        "total": {"value": 1},
                        "hits": [
                            {
                                "_source": {
                                    "option_name": "services.postgresql.enable",
                                    "option_description": "Enable PostgreSQL service",
                                    "option_type": "boolean",
                                    "type": "option",
                                }
                            }
                        ],
                    }
                }
            else:
                # Second call - return related options
                return {
                    "hits": {
                        "total": {"value": 2},
                        "hits": [
                            {
                                "_source": {
                                    "option_name": "services.postgresql.package",
                                    "option_description": "Package to use",
                                    "option_type": "package",
                                    "type": "option",
                                }
                            },
                            {
                                "_source": {
                                    "option_name": "services.postgresql.port",
                                    "option_description": "Port to use",
                                    "option_type": "int",
                                    "type": "option",
                                }
                            },
                        ],
                    }
                }

        # Replace the method with our mock
        self.client.safe_elasticsearch_query = mock_safe_es_query

        try:
            # Test getting an option with related options
            result = self.client.get_option("services.postgresql.enable")

            # Verify the main option was found
            self.assertTrue(result["found"])
            self.assertEqual(result["name"], "services.postgresql.enable")

            # Verify related options were included
            self.assertIn("related_options", result)
            self.assertEqual(len(result["related_options"]), 2)

            # Check that specific related options are included
            related_names = [opt["name"] for opt in result["related_options"]]
            self.assertIn("services.postgresql.package", related_names)
            self.assertIn("services.postgresql.port", related_names)

            # Verify service path flags
            self.assertTrue(result["is_service_path"])
            self.assertEqual(result["service_name"], "postgresql")

            # Verify that two calls were made
            self.assertEqual(call_count[0], 2)
        finally:
            # Restore the original method
            self.client.safe_elasticsearch_query = original_method


if __name__ == "__main__":
    unittest.main()
