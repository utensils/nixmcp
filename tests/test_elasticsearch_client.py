"""Tests for the ElasticsearchClient in the NixMCP server."""

import unittest
from unittest.mock import patch

# Import the ElasticsearchClient class
from nixmcp.server import ElasticsearchClient


class TestElasticsearchClient(unittest.TestCase):
    """Test the ElasticsearchClient class."""

    def setUp(self):
        """Set up test fixtures."""
        # We'll create a fresh client for each test
        self.client = ElasticsearchClient()

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

    @patch("nixmcp.utils.helpers.make_http_request")
    def test_stable_channel_usage(self, mock_make_request):
        """Test that stable channel can be used for searches."""
        # Mock successful response for stable channel
        mock_make_request.return_value = {
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

        # Create client and set to stable channel
        client = ElasticsearchClient()
        client.set_channel("stable")

        # Verify the channel was set correctly - stable points to 24.11 currently
        self.assertIn("24.11", client.es_packages_url)
        self.assertNotIn("unstable", client.es_packages_url)

        # Test search using the stable channel
        result = client.search_packages("python")

        # Verify results came back correctly
        self.assertNotIn("error", result)
        self.assertEqual(result["count"], 1)
        self.assertEqual(len(result["packages"]), 1)
        self.assertEqual(result["packages"][0]["name"], "python311")
        self.assertEqual(result["packages"][0]["channel"], "nixos-24.11")

    @patch("nixmcp.utils.helpers.make_http_request")
    def test_connection_error_handling(self, mock_make_request):
        """Test handling of connection errors."""
        # Simulate a connection error
        mock_make_request.return_value = {"error": "Failed to connect to server"}

        # Attempt to search packages
        result = self.client.search_packages("python")

        # Check the result
        self.assertIn("error", result)
        self.assertIn("connect", result["error"].lower())

    @patch("nixmcp.utils.helpers.make_http_request")
    def test_timeout_error_handling(self, mock_make_request):
        """Test handling of timeout errors."""
        # Simulate a timeout error
        mock_make_request.return_value = {"error": "Request timed out"}

        # Attempt to search packages
        result = self.client.search_packages("python")

        # Check the result
        self.assertIn("error", result)
        self.assertIn("timed out", result["error"].lower())

    @patch("nixmcp.utils.helpers.make_http_request")
    def test_server_error_handling(self, mock_make_request):
        """Test handling of server errors (5xx)."""
        # Simulate a server error
        mock_make_request.return_value = {"error": "Server error (500)"}

        # Attempt to search packages
        result = self.client.search_packages("python")

        # Check the result
        self.assertIn("error", result)
        self.assertIn("server error", result["error"].lower())

    @patch("nixmcp.utils.helpers.make_http_request")
    def test_authentication_error_handling(self, mock_make_request):
        """Test handling of authentication errors."""
        # Simulate auth errors
        mock_make_request.return_value = {"error": "Authentication failed"}

        # Attempt to search packages
        result = self.client.search_packages("python")

        # Check the result
        self.assertIn("error", result)
        self.assertIn("authentication", result["error"].lower())

    @patch("nixmcp.clients.elasticsearch_client.ElasticsearchClient.safe_elasticsearch_query")
    def test_bad_query_handling(self, mock_safe_query):
        """Test handling of bad query syntax."""
        # Simulate a bad query response directly from safe_elasticsearch_query
        mock_safe_query.return_value = {"error": "Invalid query syntax"}

        # Attempt to search packages
        result = self.client.search_packages("invalid:query:syntax")

        # Check the result
        self.assertIn("error", result)
        self.assertEqual("Invalid query syntax", result["error"])

    @patch("nixmcp.utils.helpers.make_http_request")
    def test_search_packages_with_wildcard(self, mock_make_request):
        """Test searching packages with wildcard pattern."""
        # Mock successful response
        mock_make_request.return_value = {
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

        # Test with wildcard query
        result = self.client.search_packages("python*")

        # Verify the result has the expected structure
        self.assertNotIn("error", result)
        self.assertEqual(result["count"], 1)
        self.assertEqual(len(result["packages"]), 1)
        self.assertEqual(result["packages"][0]["name"], "python311")
        self.assertEqual(result["packages"][0]["version"], "3.11.0")

        # Verify the query structure (we can check the args passed to our mock)
        args, kwargs = mock_make_request.call_args
        self.assertEqual(kwargs.get("method"), "POST")
        self.assertIsNotNone(kwargs.get("json_data"))

        query_data = kwargs.get("json_data")
        self.assertIn("query", query_data)
        # Check for wildcard handling in the query structure
        if "query_string" in query_data["query"]:
            self.assertTrue(query_data["query"]["query_string"]["analyze_wildcard"])
        elif "bool" in query_data["query"]:
            self.assertIn("should", query_data["query"]["bool"])

    @patch("nixmcp.utils.helpers.make_http_request")
    def test_get_option_related_options(self, mock_make_request):
        """Test fetching related options for service paths."""
        # Set up response sequence for main option and related options
        mock_make_request.side_effect = [
            # First response for the main option
            {
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
            },
            # Second response for related options
            {
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
            },
        ]

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

        # Verify that two requests were made (one for main option, one for related)
        self.assertEqual(mock_make_request.call_count, 2)


if __name__ == "__main__":
    unittest.main()
