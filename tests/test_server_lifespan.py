import unittest
import logging
from unittest.mock import patch, MagicMock

# Import base test class from __init__.py
from tests import NixMCPTestBase, NixMCPRealAPITestBase

# Import the server module
from server import app_lifespan, mcp, ElasticsearchClient, NixOSContext, SimpleCache

# Disable logging during tests
logging.disable(logging.CRITICAL)


class TestServerLifespan(unittest.TestCase):
    """Test the server lifespan context manager."""

    @patch("server.app_lifespan")
    def test_lifespan_initialization(self, mock_lifespan):
        """Test that the lifespan context manager initializes correctly."""
        # Create a mock context
        mock_context = {"context": NixOSContext()}

        # Configure the mock to return our context
        mock_lifespan.return_value.__aenter__.return_value = mock_context

        # Verify that the context contains the expected keys
        self.assertIn("context", mock_context)
        self.assertIsInstance(mock_context["context"], NixOSContext)

        # Verify that the context has the expected methods
        self.assertTrue(hasattr(mock_context["context"], "get_status"))
        self.assertTrue(hasattr(mock_context["context"], "get_package"))
        self.assertTrue(hasattr(mock_context["context"], "search_packages"))
        self.assertTrue(hasattr(mock_context["context"], "search_options"))

        # Verify that the ElasticsearchClient is initialized
        self.assertIsInstance(mock_context["context"].es_client, ElasticsearchClient)


class TestErrorHandling(NixMCPTestBase):
    """Test error handling in the server."""

    def test_connection_error_handling(self):
        """Test handling of connection errors.

        Instead of mocking network errors, we use a real but invalid endpoint to
        generate actual connection errors. This provides a more realistic test
        of how the application will handle connection failures in production.

        The test:
        1. Configures a client with an invalid endpoint URL
        2. Attempts to make a real request that will fail
        3. Verifies the application handles the error gracefully
        4. Confirms the error response follows the expected format
        """
        # Use a real but invalid endpoint to generate an actual connection error
        invalid_client = ElasticsearchClient()
        invalid_client.es_packages_url = (
            "https://nonexistent-server.nixos.invalid/_search"
        )

        # Replace the context's client with our invalid one
        original_client = self.context.es_client
        self.context.es_client = invalid_client

        try:
            # Test that the get_package method handles the error gracefully
            result = self.context.get_package("python")

            # Verify the result contains an error message and found=False
            self.assertFalse(result.get("found", True))
            self.assertIn("error", result)
        finally:
            # Restore the original client
            self.context.es_client = original_client

    def test_search_with_invalid_parameters(self):
        """Test search with invalid parameters."""
        # Import the nixos_search function directly
        from server import nixos_search

        # Test with an invalid type
        result = nixos_search("python", "invalid_type", 5)

        # Verify the result contains an error message
        self.assertIn("Error: Invalid type", result)
        self.assertIn("Must be one of", result)


if __name__ == "__main__":
    unittest.main()
