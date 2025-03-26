"""Tests for the ElasticsearchClient in the NixMCP server."""

import unittest
from unittest.mock import patch, MagicMock
import requests

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

        # Change channel
        client.set_channel("24.11")
        self.assertIn("24.11", client.es_packages_url)
        self.assertNotIn("unstable", client.es_packages_url)

        # Invalid channel should fall back to default
        client.set_channel("invalid-channel")
        self.assertIn("unstable", client.es_packages_url)

    @patch("requests.post")
    def test_connection_error_handling(self, mock_post):
        """Test handling of connection errors."""
        # Simulate a connection error
        mock_post.side_effect = requests.exceptions.ConnectionError("Failed to connect")

        # Attempt to search packages
        result = self.client.search_packages("python")

        # Check the result
        self.assertIn("error", result)
        self.assertIn("connect", result["error"].lower())

    @patch("requests.post")
    def test_timeout_error_handling(self, mock_post):
        """Test handling of timeout errors."""
        # Simulate a timeout error
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        # Attempt to search packages
        result = self.client.search_packages("python")

        # Check the result
        self.assertIn("error", result)
        self.assertIn("timed out", result["error"].lower())

    @patch("requests.post")
    def test_server_error_handling(self, mock_post):
        """Test handling of server errors (5xx)."""
        # Simulate a server error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        # Attempt to search packages
        result = self.client.search_packages("python")

        # Check the result
        self.assertIn("error", result)
        self.assertIn("server error", result["error"].lower())

    @patch("requests.post")
    def test_authentication_error_handling(self, mock_post):
        """Test handling of authentication errors."""
        # Simulate auth errors
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        # Attempt to search packages
        result = self.client.search_packages("python")

        # Check the result
        self.assertIn("error", result)
        self.assertIn("authentication", result["error"].lower())

    @patch("requests.post")
    def test_bad_query_handling(self, mock_post):
        """Test handling of bad query syntax."""
        # Simulate a bad query response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad query syntax"}
        mock_post.return_value = mock_response

        # Attempt to search packages
        result = self.client.search_packages("invalid:query:syntax")

        # Check the result
        self.assertIn("error", result)
        self.assertIn("invalid query", result["error"].lower())

    @patch("requests.post")
    def test_search_packages_with_wildcard(self, mock_post):
        """Test searching packages with wildcard pattern."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
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
        mock_post.return_value = mock_response

        # Test with wildcard query
        result = self.client.search_packages("python*")

        # Verify the result has the expected structure
        self.assertNotIn("error", result)
        self.assertEqual(result["count"], 1)
        self.assertEqual(len(result["packages"]), 1)
        self.assertEqual(result["packages"][0]["name"], "python311")
        self.assertEqual(result["packages"][0]["version"], "3.11.0")

        # Verify the query used the wildcard
        args, kwargs = mock_post.call_args
        query_data = kwargs.get("json")
        self.assertIn("query", query_data)
        # Check for wildcard handling in the query structure
        if "query_string" in query_data["query"]:
            self.assertTrue(query_data["query"]["query_string"]["analyze_wildcard"])
        elif "bool" in query_data["query"]:
            self.assertIn("should", query_data["query"]["bool"])

    @patch("requests.post")
    def test_get_option_related_options(self, mock_post):
        """Test fetching related options for service paths."""
        # First mock response for the main option
        main_response = MagicMock()
        main_response.status_code = 200
        main_response.json.return_value = {
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

        # Second mock response for related options
        related_response = MagicMock()
        related_response.status_code = 200
        related_response.json.return_value = {
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

        # Configure mock to return different responses on consecutive calls
        mock_post.side_effect = [main_response, related_response]

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
        self.assertEqual(mock_post.call_count, 2)


if __name__ == "__main__":
    unittest.main()
