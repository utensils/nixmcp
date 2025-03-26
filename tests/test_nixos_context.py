import unittest
from unittest.mock import patch
from nixmcp.contexts.nixos_context import NixOSContext


class TestNixOSContext(unittest.TestCase):
    """Test suite for the NixOSContext class."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock the ElasticsearchClient to avoid real API calls
        with patch("nixmcp.clients.elasticsearch_client.ElasticsearchClient") as mock_client:
            self.es_client_mock = mock_client.return_value
            self.context = NixOSContext()
            # Replace the real client with our mock
            self.context.es_client = self.es_client_mock

    def test_get_status(self):
        """Test get_status method."""
        # Configure mock
        self.es_client_mock.cache.get_stats.return_value = {"size": 10, "hits": 5, "misses": 2}

        # Call the method
        status = self.context.get_status()

        # Verify the result
        self.assertEqual(status["status"], "ok")
        self.assertEqual(status["name"], "NixMCP")
        self.assertTrue("cache_stats" in status)
        self.assertEqual(status["cache_stats"], {"size": 10, "hits": 5, "misses": 2})

    def test_search_programs(self):
        """Test search_programs method."""
        # Configure mock
        expected_result = {
            "count": 2,
            "packages": [
                {
                    "name": "vim",
                    "version": "9.0.1403",
                    "description": "The most popular clone of the VI editor",
                    "programs": ["vim", "vimdiff"],
                },
                {
                    "name": "neovim",
                    "version": "0.9.1",
                    "description": "Vim text editor fork focused on extensibility and usability",
                    "programs": ["nvim"],
                },
            ],
        }
        self.es_client_mock.search_programs.return_value = expected_result

        # Call the method
        result = self.context.search_programs("vim", 10)

        # Verify the method called the client correctly
        self.es_client_mock.search_programs.assert_called_once_with("vim", 10)

        # Verify the result
        self.assertEqual(result, expected_result)

    def test_search_packages_with_version(self):
        """Test search_packages_with_version method."""
        # Configure mock
        expected_result = {
            "count": 1,
            "packages": [
                {
                    "name": "python311",
                    "version": "3.11.6",
                    "description": "A high-level dynamically-typed programming language",
                }
            ],
        }
        self.es_client_mock.search_packages_with_version.return_value = expected_result

        # Call the method
        result = self.context.search_packages_with_version("python", "3.11.*", 10)

        # Verify the method called the client correctly
        self.es_client_mock.search_packages_with_version.assert_called_once_with("python", "3.11.*", 10)

        # Verify the result
        self.assertEqual(result, expected_result)

    def test_advanced_query(self):
        """Test advanced_query method."""
        # Configure mock
        expected_result = {"hits": {"total": {"value": 1}, "hits": [{"_source": {"package_attr_name": "python311"}}]}}
        self.es_client_mock.advanced_query.return_value = expected_result

        # Call the method
        result = self.context.advanced_query("packages", "package_attr_name:python* AND package_version:3.11*", 10)

        # Verify the method called the client correctly
        self.es_client_mock.advanced_query.assert_called_once_with(
            "packages", "package_attr_name:python* AND package_version:3.11*", 10
        )

        # Verify the result
        self.assertEqual(result, expected_result)

    def test_get_package_stats(self):
        """Test get_package_stats method."""
        # Configure mock
        expected_result = {
            "aggregations": {
                "channels": {"buckets": [{"key": "unstable", "doc_count": 100}]},
                "licenses": {"buckets": [{"key": "MIT", "doc_count": 50}]},
                "platforms": {"buckets": [{"key": "x86_64-linux", "doc_count": 80}]},
            }
        }
        self.es_client_mock.get_package_stats.return_value = expected_result

        # Call the method
        result = self.context.get_package_stats("python*")

        # Verify the method called the client correctly
        self.es_client_mock.get_package_stats.assert_called_once_with("python*")

        # Verify the result
        self.assertEqual(result, expected_result)


if __name__ == "__main__":
    unittest.main()
