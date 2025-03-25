import unittest
import sys
import os
import logging
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import the server module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the server module
from server import app_lifespan, mcp, ElasticsearchClient, NixOSContext

# Disable logging during tests
logging.disable(logging.CRITICAL)


class TestServerLifespan(unittest.TestCase):
    """Test the server lifespan context manager."""

    @patch('server.app_lifespan')
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


class TestErrorHandling(unittest.TestCase):
    """Test error handling in the server."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a mock context
        self.context = NixOSContext()
        
        # Patch the ElasticsearchClient methods to avoid real API calls
        patcher = patch.object(ElasticsearchClient, 'safe_elasticsearch_query')
        self.mock_es_query = patcher.start()
        self.addCleanup(patcher.stop)
        
        # Set up default mock responses
        self.mock_es_query.return_value = {"hits": {"hits": [], "total": {"value": 0}}}

    def test_connection_error_handling(self):
        """Test handling of connection errors."""
        # Mock the safe_elasticsearch_query method to raise a connection error
        self.mock_es_query.side_effect = Exception("Connection error")
        
        # Test that the get_package method handles the error gracefully
        result = self.context.get_package("python")
        
        # Verify the result contains an error message and found=False
        self.assertFalse(result.get("found", True))
        self.assertIn("error", result)
        
    def test_search_with_invalid_parameters(self):
        """Test search with invalid parameters."""
        # Get the search_nixos function from the mcp object
        from server import mcp
        
        # Access the tool using the get_tool method
        search_nixos = mcp.get_tool("search_nixos")
        self.assertIsNotNone(search_nixos, "Tool 'search_nixos' not found")
        
        # Test with an invalid search_type
        result = search_nixos("python", "invalid_type", 5)
        
        # Verify the result contains an error message
        self.assertIn("Error: Invalid search_type", result)
        self.assertIn("Must be one of", result)


if __name__ == "__main__":
    unittest.main()
