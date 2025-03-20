"""
Tests for the ModelContext class.
"""

import unittest
from unittest.mock import Mock, patch

from nixmcp.model_context import ModelContext


class TestModelContext(unittest.TestCase):
    """Test cases for the ModelContext class."""

    def setUp(self):
        """Set up test fixtures."""
        self.context = ModelContext()
        # Mock the NixosAPI to avoid actual network requests
        self.context.api = Mock()

    def test_query_package_cache(self):
        """Test that package queries use the cache."""
        # Setup mock
        mock_package = {"name": "test-package", "description": "Test package"}
        self.context.api.search_packages.return_value = [mock_package]
        
        # First call should use the API
        result1 = self.context.query_package("test-package")
        self.assertEqual(result1, mock_package)
        self.context.api.search_packages.assert_called_once_with("test-package", channel="unstable")
        
        # Reset mock to verify it's not called again
        self.context.api.search_packages.reset_mock()
        
        # Second call should use the cache
        result2 = self.context.query_package("test-package")
        self.assertEqual(result2, mock_package)
        self.context.api.search_packages.assert_not_called()

    def test_query_option_cache(self):
        """Test that option queries use the cache."""
        # Setup mock
        mock_option = {"name": "test-option", "description": "Test option"}
        self.context.api.search_options.return_value = [mock_option]
        
        # First call should use the API
        result1 = self.context.query_option("test-option")
        self.assertEqual(result1, mock_option)
        self.context.api.search_options.assert_called_once_with("test-option", channel="unstable")
        
        # Reset mock to verify it's not called again
        self.context.api.search_options.reset_mock()
        
        # Second call should use the cache
        result2 = self.context.query_option("test-option")
        self.assertEqual(result2, mock_option)
        self.context.api.search_options.assert_not_called()

    def test_format_context_packages(self):
        """Test formatting context with packages."""
        # Setup mocks
        pkg1 = {"name": "pkg1", "description": "Package 1", "version": "1.0", "homepage": "https://example.com/pkg1"}
        pkg2 = {"name": "pkg2", "description": "Package 2", "version": "2.0", "homepage": "https://example.com/pkg2"}
        
        # Mock query_package to return predefined packages
        self.context.query_package = Mock(side_effect=lambda name, **kwargs: 
            pkg1 if name == "pkg1" else pkg2 if name == "pkg2" else None
        )
        
        # Test formatting with packages only
        result = self.context.format_context(packages=["pkg1", "pkg2"])
        
        # Check that the result contains package information
        self.assertIn("NixOS Packages:", result)
        self.assertIn("pkg1: Package 1", result)
        self.assertIn("Version: 1.0", result)
        self.assertIn("pkg2: Package 2", result)
        self.assertIn("Version: 2.0", result)

    def test_format_context_options(self):
        """Test formatting context with options."""
        # Setup mocks
        opt1 = {"name": "opt1", "description": "Option 1", "type": "boolean", "default": "false"}
        opt2 = {"name": "opt2", "description": "Option 2", "type": "string", "default": "''"}
        
        # Mock query_option to return predefined options
        self.context.query_option = Mock(side_effect=lambda name, **kwargs: 
            opt1 if name == "opt1" else opt2 if name == "opt2" else None
        )
        
        # Test formatting with options only
        result = self.context.format_context(options=["opt1", "opt2"])
        
        # Check that the result contains option information
        self.assertIn("NixOS Options:", result)
        self.assertIn("opt1: Option 1", result)
        self.assertIn("Type: boolean", result)
        self.assertIn("opt2: Option 2", result)
        self.assertIn("Type: string", result)

    def test_format_context_max_entries(self):
        """Test formatting context with max_entries limit."""
        # Setup mocks for 3 packages
        self.context.query_package = Mock(return_value={"name": "test", "description": "Test"})
        
        # Test with max_entries=2
        result = self.context.format_context(packages=["pkg1", "pkg2", "pkg3"], max_entries=2)
        
        # Should only query the first 2 packages
        self.assertEqual(self.context.query_package.call_count, 2)


if __name__ == "__main__":
    unittest.main()