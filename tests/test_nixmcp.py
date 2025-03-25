import unittest
import sys
import os
import json
import logging
from unittest.mock import patch
import time

# Add the parent directory to the path so we can import the server module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the server module
from server import ElasticsearchClient, NixOSContext, SimpleCache

# Disable logging during tests
logging.disable(logging.CRITICAL)


class TestElasticsearchClient(unittest.TestCase):
    """Test the ElasticsearchClient class with real API calls."""

    def setUp(self):
        """Set up the test environment."""
        self.client = ElasticsearchClient()
        # Use a smaller cache for testing
        self.client.cache = SimpleCache(max_size=10, ttl=60)

    def test_search_packages(self):
        """Test searching for packages."""
        # Test with a common package that should always exist
        result = self.client.search_packages("python", limit=5)
        
        # Verify the structure of the response
        self.assertIn("packages", result)
        self.assertIn("count", result)
        self.assertIsInstance(result["packages"], list)
        self.assertGreater(len(result["packages"]), 0)
        
        # Verify the structure of a package
        package = result["packages"][0]
        self.assertIn("name", package)
        self.assertIn("description", package)
        
        # Test with a wildcard search
        result = self.client.search_packages("pyth*", limit=5)
        self.assertGreater(len(result["packages"]), 0)
        
        # Test with a non-existent package
        result = self.client.search_packages("thisshouldnotexistasapackage12345", limit=5)
        self.assertEqual(len(result["packages"]), 0)

    def test_search_options(self):
        """Test searching for options."""
        # Test with a common option that should always exist
        result = self.client.search_options("services.nginx", limit=5)
        
        # Verify the structure of the response
        self.assertIn("options", result)
        self.assertIn("count", result)
        self.assertIsInstance(result["options"], list)
        self.assertGreater(len(result["options"]), 0)
        
        # Verify the structure of an option
        option = result["options"][0]
        self.assertIn("name", option)
        self.assertIn("description", option)
        
        # Test with a wildcard search
        result = self.client.search_options("services.*", limit=5)
        self.assertGreater(len(result["options"]), 0)
        
        # Test with a non-existent option
        result = self.client.search_options("thisshouldnotexistasanoption12345", limit=5)
        self.assertEqual(len(result["options"]), 0)

    def test_get_package(self):
        """Test getting a specific package."""
        # Test with a package that should always exist
        result = self.client.get_package("python")
        
        # Verify the structure of the response
        self.assertIn("name", result)
        self.assertIn("description", result)
        self.assertIn("version", result)
        self.assertTrue(result.get("found", False))
        
        # Test with a non-existent package
        result = self.client.get_package("thisshouldnotexistasapackage12345")
        self.assertFalse(result.get("found", True))
        self.assertIn("error", result)

    def test_get_option(self):
        """Test getting a specific option."""
        # Test with an option that should always exist
        result = self.client.get_option("services.nginx.enable")
        
        # Verify the structure of the response
        self.assertIn("name", result)
        self.assertIn("description", result)
        self.assertIn("type", result)
        self.assertTrue(result.get("found", False))
        
        # Test with a non-existent option
        result = self.client.get_option("thisshouldnotexistasanoption12345")
        self.assertFalse(result.get("found", True))
        self.assertIn("error", result)

    def test_search_programs(self):
        """Test searching for programs."""
        # Test with a common program that should always exist
        result = self.client.search_programs("python", limit=5)
        
        # Verify the structure of the response
        self.assertIn("packages", result)
        self.assertIn("count", result)
        self.assertIsInstance(result["packages"], list)
        self.assertGreater(len(result["packages"]), 0)
        
        # Test with a non-existent program
        result = self.client.search_programs("thisshouldnotexistasaprogram12345", limit=5)
        self.assertEqual(len(result["packages"]), 0)

    def test_advanced_query(self):
        """Test advanced query functionality."""
        # Test with a query that should return results
        query = "package_attr_name:python"
        result = self.client.advanced_query("packages", query, limit=5)
        
        # Verify we got hits
        self.assertIn("hits", result)
        self.assertGreater(len(result["hits"]["hits"]), 0)
        
        # Test with an option query
        query = "option_name:services.nginx*"
        result = self.client.advanced_query("options", query, limit=5)
        self.assertGreater(len(result["hits"]["hits"]), 0)

    def test_cache(self):
        """Test that the cache is working."""
        # Clear the cache
        self.client.cache.clear()
        
        # Make a request that should be cached
        self.client.search_packages("python", limit=5)
        
        # Check cache stats
        stats = self.client.cache.get_stats()
        self.assertEqual(stats["hits"], 0)
        self.assertEqual(stats["misses"], 1)
        
        # Make the same request again
        self.client.search_packages("python", limit=5)
        
        # Check cache stats again
        stats = self.client.cache.get_stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)


class TestSimpleCache(unittest.TestCase):
    """Test the SimpleCache class."""

    def setUp(self):
        """Set up the test environment."""
        self.cache = SimpleCache(max_size=3, ttl=1)  # Small cache with 1 second TTL

    def test_cache_set_get(self):
        """Test setting and getting values from the cache."""
        # Set a value
        self.cache.set("key1", "value1")
        
        # Get the value
        value = self.cache.get("key1")
        self.assertEqual(value, "value1")
        
        # Get a non-existent key
        value = self.cache.get("nonexistent")
        self.assertIsNone(value)

    def test_cache_expiration(self):
        """Test that cache entries expire after TTL."""
        # Set a value
        self.cache.set("key1", "value1")
        
        # Get the value immediately
        value = self.cache.get("key1")
        self.assertEqual(value, "value1")
        
        # Wait for TTL to expire
        time.sleep(1.1)
        
        # Get the value again
        value = self.cache.get("key1")
        self.assertIsNone(value)

    def test_cache_max_size(self):
        """Test that cache respects max size."""
        # Fill the cache
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.set("key3", "value3")
        
        # All values should be present
        self.assertEqual(self.cache.get("key1"), "value1")
        self.assertEqual(self.cache.get("key2"), "value2")
        self.assertEqual(self.cache.get("key3"), "value3")
        
        # Add one more item, which should evict the oldest
        self.cache.set("key4", "value4")
        
        # key1 should be evicted
        self.assertIsNone(self.cache.get("key1"))
        
        # Other keys should still be present
        self.assertEqual(self.cache.get("key2"), "value2")
        self.assertEqual(self.cache.get("key3"), "value3")
        self.assertEqual(self.cache.get("key4"), "value4")

    def test_cache_stats(self):
        """Test cache statistics."""
        # Clear stats
        self.cache = SimpleCache(max_size=3, ttl=1)
        
        # Set a value
        self.cache.set("key1", "value1")
        
        # Get the value (hit)
        self.cache.get("key1")
        
        # Get a non-existent value (miss)
        self.cache.get("nonexistent")
        
        # Check stats
        stats = self.cache.get_stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["size"], 1)
        self.assertEqual(stats["max_size"], 3)
        self.assertEqual(stats["ttl"], 1)
        self.assertEqual(stats["hit_ratio"], 0.5)


class TestNixOSContext(unittest.TestCase):
    """Test the NixOSContext class."""

    def setUp(self):
        """Set up the test environment."""
        self.context = NixOSContext()

    def test_get_status(self):
        """Test getting server status."""
        status = self.context.get_status()
        
        # Verify the structure of the response
        self.assertIn("status", status)
        self.assertIn("version", status)
        self.assertIn("name", status)
        self.assertIn("description", status)
        self.assertIn("cache_stats", status)
        
        # Verify the status is ok
        self.assertEqual(status["status"], "ok")

    def test_search_packages(self):
        """Test searching for packages through the context."""
        result = self.context.search_packages("python", limit=5)
        
        # Verify the structure of the response
        self.assertIn("packages", result)
        self.assertIn("count", result)
        self.assertIsInstance(result["packages"], list)
        self.assertGreater(len(result["packages"]), 0)

    def test_search_options(self):
        """Test searching for options through the context."""
        result = self.context.search_options("services.nginx", limit=5)
        
        # Verify the structure of the response
        self.assertIn("options", result)
        self.assertIn("count", result)
        self.assertIsInstance(result["options"], list)
        self.assertGreater(len(result["options"]), 0)

    def test_get_package(self):
        """Test getting a specific package through the context."""
        result = self.context.get_package("python")
        
        # Verify the structure of the response
        self.assertIn("name", result)
        self.assertIn("description", result)
        self.assertTrue(result.get("found", False))

    def test_get_option(self):
        """Test getting a specific option through the context."""
        result = self.context.get_option("services.nginx.enable")
        
        # Verify the structure of the response
        self.assertIn("name", result)
        self.assertIn("description", result)
        self.assertTrue(result.get("found", False))


if __name__ == "__main__":
    unittest.main()
