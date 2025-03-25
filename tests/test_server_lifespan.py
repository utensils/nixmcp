import unittest
import sys
import os
import logging
from unittest.mock import patch, AsyncMock, MagicMock

# Add the parent directory to the path so we can import the server module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the server module
from server import app_lifespan, mcp, ElasticsearchClient, NixOSContext

# Disable logging during tests
logging.disable(logging.CRITICAL)


class TestServerLifespan(unittest.TestCase):
    """Test the server lifespan context manager."""

    async def test_lifespan_initialization(self):
        """Test that the lifespan context manager initializes correctly."""
        # Create a mock FastMCP instance
        mock_mcp = MagicMock()
        
        # Create an async context manager to test the lifespan
        async with app_lifespan(mock_mcp) as context:
            # Verify that the context contains the expected keys
            self.assertIn("context", context)
            self.assertIsInstance(context["context"], NixOSContext)
            
            # Verify that the context has the expected methods
            self.assertTrue(hasattr(context["context"], "get_status"))
            self.assertTrue(hasattr(context["context"], "get_package"))
            self.assertTrue(hasattr(context["context"], "search_packages"))
            self.assertTrue(hasattr(context["context"], "search_options"))
            
            # Verify that the ElasticsearchClient is initialized
            self.assertIsInstance(context["context"].es_client, ElasticsearchClient)


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
        # Import the search_nixos function
        from server import search_nixos
        
        # Test with an invalid search_type
        result = search_nixos("python", "invalid_type", 5)
        
        # Verify the result contains an error message
        self.assertIn("Error: Invalid search_type", result)
        self.assertIn("Must be one of", result)


if __name__ == "__main__":
    unittest.main()
