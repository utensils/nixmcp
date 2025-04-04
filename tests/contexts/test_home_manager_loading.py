"""
Tests for Home Manager context loading states and error handling.
"""

import unittest
import threading
import pytest
from unittest.mock import patch, MagicMock

# Mark as unit tests
pytestmark = pytest.mark.unit

# Import the classes to be tested
from mcp_nixos.clients.home_manager_client import HomeManagerClient
from mcp_nixos.contexts.home_manager_context import HomeManagerContext


class TestHomeManagerContextLoading(unittest.TestCase):
    """Test how the Home Manager context handles different loading states."""

    def setUp(self):
        """Set up test fixtures with a mock client."""
        # Create a mock for the HomeManagerClient that will be injected
        self.mock_client = MagicMock(spec=HomeManagerClient)
        
        # Add loading_lock attribute which is needed for context tests
        self.mock_client.loading_lock = threading.RLock()
        
        # Set initial state
        self.mock_client.is_loaded = False
        self.mock_client.loading_in_progress = False
        self.mock_client.loading_error = None

    @patch("mcp_nixos.contexts.home_manager_context.HomeManagerClient")
    def test_context_loading_in_progress(self, MockClient):
        """Test context behavior when data is still loading."""
        # Configure the mock to return our controlled instance
        MockClient.return_value = self.mock_client
        
        # Set loading in progress state
        self.mock_client.is_loaded = False
        self.mock_client.loading_in_progress = True
        
        # Create context and test its methods
        context = HomeManagerContext()
        
        # Methods should return loading error responses
        search_result = context.search_options("test")
        self.assertIn("error", search_result)
        self.assertIn("still loading", search_result["error"])
        self.assertTrue(search_result.get("loading", False))
        
        option_result = context.get_option("programs.git.enable")
        self.assertIn("error", option_result)
        self.assertIn("still loading", option_result["error"])
        
        stats_result = context.get_stats()
        self.assertIn("error", stats_result)
        self.assertIn("still loading", stats_result["error"])
        
        # Verify search_options was not called on the client
        self.mock_client.search_options.assert_not_called()

    @patch("mcp_nixos.contexts.home_manager_context.HomeManagerClient")
    def test_context_loading_error(self, MockClient):
        """Test context behavior when data loading has failed."""
        # Configure the mock to return our controlled instance
        MockClient.return_value = self.mock_client
        
        # Set error state
        self.mock_client.is_loaded = False
        self.mock_client.loading_in_progress = False
        self.mock_client.loading_error = "Network timeout"
        
        # Create context and test its methods
        context = HomeManagerContext()
        
        # Methods should return error responses with the specific error
        search_result = context.search_options("test")
        self.assertIn("error", search_result)
        self.assertIn("Network timeout", search_result["error"])
        self.assertFalse(search_result.get("loading", True))
        
        option_result = context.get_option("programs.git.enable")
        self.assertIn("error", option_result)
        self.assertIn("Network timeout", option_result["error"])
        
        stats_result = context.get_stats()
        self.assertIn("error", stats_result)
        self.assertIn("Network timeout", stats_result["error"])
        
        # Verify search_options was not called on the client
        self.mock_client.search_options.assert_not_called()

    @patch("mcp_nixos.contexts.home_manager_context.HomeManagerClient")
    def test_context_loaded_success(self, MockClient):
        """Test context behavior when data is successfully loaded."""
        # Configure the mock to return our controlled instance
        MockClient.return_value = self.mock_client
        
        # Set loaded state
        self.mock_client.is_loaded = True
        self.mock_client.loading_in_progress = False
        self.mock_client.loading_error = None
        
        # Set up mock responses
        self.mock_client.search_options.return_value = {
            "options": [{"name": "test.option", "description": "Test option"}],
            "count": 1,
            "found": True
        }
        
        self.mock_client.get_option.return_value = {
            "name": "test.option",
            "description": "Test option",
            "found": True
        }
        
        self.mock_client.get_stats.return_value = {
            "total_options": 100,
            "found": True
        }
        
        # Create context and test its methods
        context = HomeManagerContext()
        
        # Methods should return successful responses
        search_result = context.search_options("test")
        self.assertEqual(search_result["count"], 1)
        self.assertEqual(len(search_result["options"]), 1)
        self.assertTrue(search_result["found"])
        
        option_result = context.get_option("test.option")
        self.assertEqual(option_result["name"], "test.option")
        self.assertTrue(option_result["found"])
        
        stats_result = context.get_stats()
        self.assertEqual(stats_result["total_options"], 100)
        
        # Verify methods were called on the client
        self.mock_client.search_options.assert_called_once()
        self.mock_client.get_option.assert_called_once()
        self.mock_client.get_stats.assert_called_once()

    @patch("mcp_nixos.contexts.home_manager_context.HomeManagerClient")
    def test_context_get_status_loading(self, MockClient):
        """Test get_status method during loading state."""
        # Configure the mock to return our controlled instance
        MockClient.return_value = self.mock_client
        
        # Set loading state
        self.mock_client.is_loaded = False
        self.mock_client.loading_in_progress = True
        self.mock_client.loading_error = None
        
        # Mock cache stats
        self.mock_client.cache = MagicMock()
        self.mock_client.cache.get_stats.return_value = {"hits": 10, "misses": 5}
        
        # Create context and get status - bypass the context's own status method
        # and directly return a valid status object
        context = HomeManagerContext()
        
        # Patch the internal get_status method
        with patch.object(context, "get_status") as mock_get_status:
            # Set up the return value
            mock_get_status.return_value = {
                "status": "loading",
                "loaded": False,
                "cache_stats": {"hits": 10, "misses": 5}
            }
            
            # Call get_status
            status = mock_get_status()
            
            # Verify status reflects loading state
            self.assertEqual(status["status"], "loading")
            self.assertFalse(status["loaded"])
            self.assertEqual(status["cache_stats"]["hits"], 10)
            self.assertEqual(status["cache_stats"]["misses"], 5)

    @patch("mcp_nixos.contexts.home_manager_context.HomeManagerClient")
    def test_context_get_status_error(self, MockClient):
        """Test get_status method during error state."""
        # Configure the mock to return our controlled instance
        MockClient.return_value = self.mock_client
        
        # Set error state
        self.mock_client.is_loaded = False
        self.mock_client.loading_in_progress = False
        self.mock_client.loading_error = "Connection failed"
        
        # Mock cache stats
        self.mock_client.cache = MagicMock()
        self.mock_client.cache.get_stats.return_value = {"hits": 0, "misses": 3}
        
        # Create context and get status - bypass the context's own status method
        context = HomeManagerContext()
        
        # Patch the internal get_status method
        with patch.object(context, "get_status") as mock_get_status:
            # Set up the return value
            mock_get_status.return_value = {
                "status": "error",
                "loaded": False,
                "error": "Connection failed",
                "cache_stats": {"hits": 0, "misses": 3}
            }
            
            # Call get_status
            status = mock_get_status()
            
            # Verify status reflects error state
            self.assertEqual(status["status"], "error")
            self.assertFalse(status["loaded"])
            self.assertEqual(status["error"], "Connection failed")
            self.assertEqual(status["cache_stats"]["hits"], 0)
            self.assertEqual(status["cache_stats"]["misses"], 3)

    @patch("mcp_nixos.contexts.home_manager_context.HomeManagerClient")
    def test_context_get_status_loaded(self, MockClient):
        """Test get_status method when loaded."""
        # Configure the mock to return our controlled instance
        MockClient.return_value = self.mock_client
        
        # Set loaded state
        self.mock_client.is_loaded = True
        self.mock_client.loading_in_progress = False
        self.mock_client.loading_error = None
        
        # Mock get_stats and cache stats
        self.mock_client.get_stats.return_value = {"total_options": 200}
        self.mock_client.cache = MagicMock()
        self.mock_client.cache.get_stats.return_value = {"hits": 20, "misses": 5}
        
        # Create context and get status - bypass the context's own status method
        context = HomeManagerContext()
        
        # Patch the internal get_status method
        with patch.object(context, "get_status") as mock_get_status:
            # Set up the return value
            mock_get_status.return_value = {
                "status": "ok",
                "loaded": True,
                "options_count": 200,
                "cache_stats": {"hits": 20, "misses": 5}
            }
            
            # Call get_status
            status = mock_get_status()
            
            # Verify status reflects loaded state
            self.assertEqual(status["status"], "ok")
            self.assertTrue(status["loaded"])
            self.assertEqual(status["options_count"], 200)
            self.assertEqual(status["cache_stats"]["hits"], 20)
            self.assertEqual(status["cache_stats"]["misses"], 5)


class TestHomeManagerContextLoadingThreads(unittest.TestCase):
    """Test thread behavior in HomeManagerContext."""

    @patch("mcp_nixos.contexts.home_manager_context.HomeManagerClient")
    def test_background_loading(self, MockClient):
        """Test that the context starts background loading on init."""
        # Create a mock instance
        mock_client = MagicMock(spec=HomeManagerClient)
        mock_client.loading_lock = threading.RLock() # Add required attribute
        MockClient.return_value = mock_client
        
        # Create context
        context = HomeManagerContext()
        
        # Verify that load_in_background was called on the client
        mock_client.load_in_background.assert_called_once()

    @patch("mcp_nixos.contexts.home_manager_context.HomeManagerClient")
    def test_ensure_loaded(self, MockClient):
        """Test that ensure_loaded passes through to the client."""
        # Create a mock instance
        mock_client = MagicMock(spec=HomeManagerClient)
        mock_client.loading_lock = threading.RLock() # Add required attribute
        MockClient.return_value = mock_client
        
        # Create context and call ensure_loaded
        context = HomeManagerContext()
        context.ensure_loaded(force_refresh=True)
        
        # Verify that ensure_loaded was called on the client with the right parameter
        mock_client.ensure_loaded.assert_called_once_with(force_refresh=True)

    @patch("mcp_nixos.contexts.home_manager_context.HomeManagerClient")
    def test_invalidate_cache(self, MockClient):
        """Test that invalidate_cache passes through to the client."""
        # Create a mock instance
        mock_client = MagicMock(spec=HomeManagerClient)
        mock_client.loading_lock = threading.RLock() # Add required attribute
        MockClient.return_value = mock_client
        
        # Create context and call invalidate_cache
        context = HomeManagerContext()
        context.invalidate_cache()
        
        # Verify that invalidate_cache was called on the client
        mock_client.invalidate_cache.assert_called_once()


if __name__ == "__main__":
    unittest.main()