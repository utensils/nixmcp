import unittest
import sys
import os
import json
import logging
from unittest.mock import patch, MagicMock
import time

# Add the parent directory to the path so we can import the server module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the server module
from server import ElasticsearchClient, NixOSContext, SimpleCache, mcp

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


class TestMCPTools(unittest.TestCase):
    """Test the MCP tools functionality."""

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

    def test_search_nixos_packages(self):
        """Test the search_nixos tool with packages."""
        # Mock the search_packages method to return test data
        with patch.object(NixOSContext, 'search_packages') as mock_search:
            mock_search.return_value = {
                "count": 2,
                "packages": [
                    {
                        "name": "python3",
                        "version": "3.10.12",
                        "description": "A high-level dynamically-typed programming language",
                        "channel": "nixos-unstable"
                    },
                    {
                        "name": "python39",
                        "version": "3.9.18",
                        "description": "Python programming language",
                        "channel": "nixos-unstable"
                    }
                ]
            }
            
            # Get the tool function from mcp
            from server import mcp
            
            # Access the tool directly from the tools list
            search_nixos = None
            for tool in mcp.tools:
                if tool.name == "search_nixos":
                    search_nixos = tool.func
                    break
                    
            self.assertIsNotNone(search_nixos, "Tool 'search_nixos' not found")
            result = search_nixos("python", "packages", 5)
            
            # Verify the result
            self.assertIn("Found 2 packages for 'python'", result)
            self.assertIn("python3", result)
            self.assertIn("3.10.12", result)
            self.assertIn("python39", result)
            
            # Verify the mock was called correctly
            mock_search.assert_called_once_with("python", 5)

    def test_search_nixos_options(self):
        """Test the search_nixos tool with options."""
        # Mock the search_options method to return test data
        with patch.object(NixOSContext, 'search_options') as mock_search:
            mock_search.return_value = {
                "count": 2,
                "options": [
                    {
                        "name": "services.nginx.enable",
                        "description": "Whether to enable nginx.",
                        "type": "boolean",
                        "default": "false"
                    },
                    {
                        "name": "services.nginx.virtualHosts",
                        "description": "Declarative vhost config",
                        "type": "attribute set",
                        "default": "{}"
                    }
                ]
            }
            
            # Get the tool function from mcp
            from server import mcp
            
            # Access the tool directly from the tools list
            search_nixos = None
            for tool in mcp.tools:
                if tool.name == "search_nixos":
                    search_nixos = tool.func
                    break
                    
            self.assertIsNotNone(search_nixos, "Tool 'search_nixos' not found")
            result = search_nixos("nginx", "options", 5)
            
            # Verify the result
            self.assertIn("Found 2 options for 'nginx'", result)
            self.assertIn("services.nginx.enable", result)
            self.assertIn("Whether to enable nginx", result)
            self.assertIn("services.nginx.virtualHosts", result)
            
            # Verify the mock was called correctly
            mock_search.assert_called_once_with("nginx", 5)

    def test_search_nixos_programs(self):
        """Test the search_nixos tool with programs."""
        # Mock the search_programs method to return test data
        with patch.object(NixOSContext, 'search_programs') as mock_search:
            mock_search.return_value = {
                "count": 2,
                "packages": [
                    {
                        "name": "python3",
                        "version": "3.10.12",
                        "description": "Python programming language",
                        "programs": ["python3", "python3.10"]
                    },
                    {
                        "name": "python39",
                        "version": "3.9.18",
                        "description": "Python programming language",
                        "programs": ["python3.9", "python39"]
                    }
                ]
            }
            
            # Get the tool function from mcp
            from server import mcp
            
            # Access the tool directly from the tools list
            search_nixos = None
            for tool in mcp.tools:
                if tool.name == "search_nixos":
                    search_nixos = tool.func
                    break
                    
            self.assertIsNotNone(search_nixos, "Tool 'search_nixos' not found")
            result = search_nixos("python", "programs", 5)
            
            # Verify the result
            self.assertIn("Found 2 packages providing programs matching 'python'", result)
            self.assertIn("python3", result)
            self.assertIn("python3.10", result)
            self.assertIn("python39", result)
            
            # Verify the mock was called correctly
            mock_search.assert_called_once_with("python", 5)

    def test_get_nixos_package(self):
        """Test the get_nixos_package tool."""
        # Mock the get_package method to return test data
        with patch.object(NixOSContext, 'get_package') as mock_get:
            mock_get.return_value = {
                "name": "python3",
                "version": "3.10.12",
                "description": "A high-level dynamically-typed programming language",
                "longDescription": "Python is a remarkably powerful dynamic programming language...",
                "license": "MIT",
                "homepage": "https://www.python.org",
                "maintainers": ["Alice", "Bob"],
                "platforms": ["x86_64-linux", "aarch64-linux"],
                "channel": "nixos-unstable",
                "programs": ["python3", "python3.10"],
                "found": True
            }
            
            # Get the tool function from mcp
            from server import mcp
            
            # Access the tool directly from the tools list
            get_nixos_package = None
            for tool in mcp.tools:
                if tool.name == "get_nixos_package":
                    get_nixos_package = tool.func
                    break
                    
            self.assertIsNotNone(get_nixos_package, "Tool 'get_nixos_package' not found")
            result = get_nixos_package("python3")
            
            # Verify the result
            self.assertIn("# python3", result)
            self.assertIn("**Version:** 3.10.12", result)
            self.assertIn("**Description:**", result)
            self.assertIn("**License:** MIT", result)
            self.assertIn("**Homepage:** https://www.python.org", result)
            self.assertIn("**Maintainers:** Alice, Bob", result)
            self.assertIn("**Platforms:** x86_64-linux, aarch64-linux", result)
            self.assertIn("**Provided Programs:** python3, python3.10", result)
            
            # Verify the mock was called correctly
            mock_get.assert_called_once_with("python3")

    def test_get_nixos_option(self):
        """Test the get_nixos_option tool."""
        # Mock the get_option method to return test data
        with patch.object(NixOSContext, 'get_option') as mock_get:
            mock_get.return_value = {
                "name": "services.nginx.enable",
                "description": "Whether to enable nginx.",
                "type": "boolean",
                "default": "false",
                "example": "true",
                "declarations": ["/nix/store/...-nixos/modules/services/web-servers/nginx/default.nix"],
                "readOnly": False,
                "found": True
            }
            
            # Get the tool function from mcp
            from server import mcp
            
            # Access the tool directly from the tools list
            get_nixos_option = None
            for tool in mcp.tools:
                if tool.name == "get_nixos_option":
                    get_nixos_option = tool.func
                    break
                    
            self.assertIsNotNone(get_nixos_option, "Tool 'get_nixos_option' not found")
            result = get_nixos_option("services.nginx.enable")
            
            # Verify the result
            self.assertIn("# services.nginx.enable", result)
            self.assertIn("**Description:** Whether to enable nginx.", result)
            self.assertIn("**Type:** boolean", result)
            self.assertIn("**Default:** false", result)
            self.assertIn("**Example:**", result)
            self.assertIn("**Declared in:**", result)
            
            # Verify the mock was called correctly
            mock_get.assert_called_once_with("services.nginx.enable")

    def test_advanced_search(self):
        """Test the advanced_search tool."""
        # Mock the advanced_query method to return test data
        with patch.object(NixOSContext, 'advanced_query') as mock_query:
            mock_query.return_value = {
                "hits": {
                    "total": {"value": 2},
                    "hits": [
                        {
                            "_score": 10.5,
                            "_source": {
                                "package_attr_name": "python3",
                                "package_version": "3.10.12",
                                "package_description": "Python programming language"
                            }
                        },
                        {
                            "_score": 8.2,
                            "_source": {
                                "package_attr_name": "python39",
                                "package_version": "3.9.18",
                                "package_description": "Python programming language"
                            }
                        }
                    ]
                }
            }
            
            # Get the tool function from mcp
            from server import mcp
            
            # Access the tool directly from the tools list
            advanced_search = None
            for tool in mcp.tools:
                if tool.name == "advanced_search":
                    advanced_search = tool.func
                    break
                    
            self.assertIsNotNone(advanced_search, "Tool 'advanced_search' not found")
            result = advanced_search("package_programs:python*", "packages", 5)
            
            # Verify the result
            self.assertIn("Found 2 results for query 'package_programs:python*'", result)
            self.assertIn("python3", result)
            self.assertIn("3.10.12", result)
            self.assertIn("python39", result)
            self.assertIn("score: 10.50", result)
            
            # Verify the mock was called correctly
            mock_query.assert_called_once_with("packages", "package_programs:python*", 5)

    def test_package_statistics(self):
        """Test the package_statistics tool."""
        # Mock the get_package_stats method to return test data
        with patch.object(NixOSContext, 'get_package_stats') as mock_stats:
            mock_stats.return_value = {
                "aggregations": {
                    "channels": {
                        "buckets": [
                            {"key": "nixos-unstable", "doc_count": 80000},
                            {"key": "nixos-23.11", "doc_count": 75000}
                        ]
                    },
                    "licenses": {
                        "buckets": [
                            {"key": "MIT", "doc_count": 20000},
                            {"key": "GPL", "doc_count": 15000}
                        ]
                    },
                    "platforms": {
                        "buckets": [
                            {"key": "x86_64-linux", "doc_count": 70000},
                            {"key": "aarch64-linux", "doc_count": 60000}
                        ]
                    }
                }
            }
            
            # Mock the cache stats
            with patch.object(SimpleCache, 'get_stats') as mock_cache_stats:
                mock_cache_stats.return_value = {
                    "size": 100,
                    "max_size": 500,
                    "ttl": 600,
                    "hits": 800,
                    "misses": 200,
                    "hit_ratio": 0.8
                }
                
                # Get the tool function from mcp
                from server import mcp
                
                # Access the tool directly from the tools list
                package_statistics = None
                for tool in mcp.tools:
                    if tool.name == "package_statistics":
                        package_statistics = tool.func
                        break
                        
                self.assertIsNotNone(package_statistics, "Tool 'package_statistics' not found")
                result = package_statistics("*")
                
                # Verify the result
                self.assertIn("# NixOS Package Statistics", result)
                self.assertIn("## Distribution by Channel", result)
                self.assertIn("nixos-unstable: 80000 packages", result)
                self.assertIn("## Distribution by License", result)
                self.assertIn("MIT: 20000 packages", result)
                self.assertIn("## Distribution by Platform", result)
                self.assertIn("x86_64-linux: 70000 packages", result)
                self.assertIn("## Cache Statistics", result)
                self.assertIn("Cache size: 100/500 entries", result)
                self.assertIn("Hit ratio: 80.0%", result)
                
                # Verify the mocks were called correctly
                mock_stats.assert_called_once_with("*")
                mock_cache_stats.assert_called_once()

    def test_version_search(self):
        """Test the version_search tool."""
        # Mock the search_packages_with_version method to return test data
        with patch.object(NixOSContext, 'search_packages_with_version') as mock_search:
            mock_search.return_value = {
                "count": 2,
                "packages": [
                    {
                        "name": "python310",
                        "version": "3.10.12",
                        "description": "Python 3.10",
                        "channel": "nixos-unstable"
                    },
                    {
                        "name": "python311",
                        "version": "3.11.6",
                        "description": "Python 3.11",
                        "channel": "nixos-unstable"
                    }
                ]
            }
            
            # Get the tool function from mcp
            from server import mcp
            
            # Access the tool directly from the tools list
            version_search = None
            for tool in mcp.tools:
                if tool.name == "version_search":
                    version_search = tool.func
                    break
                    
            self.assertIsNotNone(version_search, "Tool 'version_search' not found")
            result = version_search("python", "3.1*", 5)
            
            # Verify the result
            self.assertIn("Found 2 packages matching 'python' with version pattern '3.1*'", result)
            self.assertIn("python310 (3.10.12)", result)
            self.assertIn("Python 3.10", result)
            self.assertIn("python311 (3.11.6)", result)
            
            # Verify the mock was called correctly
            mock_search.assert_called_once_with("python", "3.1*", 5)


class TestMCPResources(unittest.TestCase):
    """Test the MCP resources functionality."""
    
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

    def test_status_resource(self):
        """Test the status resource."""
        # Mock the get_status method
        with patch.object(NixOSContext, 'get_status') as mock_status:
            mock_status.return_value = {
                "status": "ok",
                "version": "1.0.0",
                "name": "NixMCP",
                "description": "NixOS HTTP-based Model Context Protocol Server",
                "cache_stats": {
                    "size": 100,
                    "max_size": 500,
                    "ttl": 600,
                    "hits": 800,
                    "misses": 200,
                    "hit_ratio": 0.8
                }
            }
            
            # Import the resource function
            from server import status_resource
            
            # Call the resource function
            result = status_resource()
            
            # Verify the result
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["version"], "1.0.0")
            self.assertEqual(result["name"], "NixMCP")
            self.assertIn("cache_stats", result)
            
            # Verify the mock was called
            mock_status.assert_called_once()

    def test_package_resource(self):
        """Test the package resource."""
        # Mock the get_package method
        with patch.object(NixOSContext, 'get_package') as mock_get:
            mock_get.return_value = {
                "name": "python3",
                "version": "3.10.12",
                "description": "Python programming language",
                "found": True
            }
            
            # Import the resource function
            from server import package_resource
            
            # Call the resource function
            result = package_resource("python3")
            
            # Verify the result
            self.assertEqual(result["name"], "python3")
            self.assertEqual(result["version"], "3.10.12")
            self.assertTrue(result["found"])
            
            # Verify the mock was called correctly
            mock_get.assert_called_once_with("python3")

    def test_search_packages_resource(self):
        """Test the search_packages resource."""
        # Mock the search_packages method
        with patch.object(NixOSContext, 'search_packages') as mock_search:
            mock_search.return_value = {
                "count": 2,
                "packages": [
                    {"name": "python3", "description": "Python 3"},
                    {"name": "python39", "description": "Python 3.9"}
                ]
            }
            
            # Import the resource function
            from server import search_packages_resource
            
            # Call the resource function
            result = search_packages_resource("python")
            
            # Verify the result
            self.assertEqual(result["count"], 2)
            self.assertEqual(len(result["packages"]), 2)
            self.assertEqual(result["packages"][0]["name"], "python3")
            
            # Verify the mock was called correctly
            mock_search.assert_called_once_with("python")

    def test_search_options_resource(self):
        """Test the search_options resource."""
        # Mock the search_options method
        with patch.object(NixOSContext, 'search_options') as mock_search:
            mock_search.return_value = {
                "count": 2,
                "options": [
                    {"name": "services.nginx.enable", "description": "Enable nginx"},
                    {"name": "services.nginx.virtualHosts", "description": "Virtual hosts"}
                ]
            }
            
            # Import the resource function
            from server import search_options_resource
            
            # Call the resource function
            result = search_options_resource("nginx")
            
            # Verify the result
            self.assertEqual(result["count"], 2)
            self.assertEqual(len(result["options"]), 2)
            self.assertEqual(result["options"][0]["name"], "services.nginx.enable")
            
            # Verify the mock was called correctly
            mock_search.assert_called_once_with("nginx")

    def test_option_resource(self):
        """Test the option resource."""
        # Mock the get_option method
        with patch.object(NixOSContext, 'get_option') as mock_get:
            mock_get.return_value = {
                "name": "services.nginx.enable",
                "description": "Whether to enable nginx.",
                "type": "boolean",
                "default": "false",
                "found": True
            }
            
            # Import the resource function
            from server import option_resource
            
            # Call the resource function
            result = option_resource("services.nginx.enable")
            
            # Verify the result
            self.assertEqual(result["name"], "services.nginx.enable")
            self.assertEqual(result["type"], "boolean")
            self.assertTrue(result["found"])
            
            # Verify the mock was called correctly
            mock_get.assert_called_once_with("services.nginx.enable")

    def test_search_programs_resource(self):
        """Test the search_programs resource."""
        # Mock the search_programs method
        with patch.object(NixOSContext, 'search_programs') as mock_search:
            mock_search.return_value = {
                "count": 2,
                "packages": [
                    {"name": "python3", "programs": ["python3", "python3.10"]},
                    {"name": "python39", "programs": ["python3.9"]}
                ]
            }
            
            # Import the resource function
            from server import search_programs_resource
            
            # Call the resource function
            result = search_programs_resource("python")
            
            # Verify the result
            self.assertEqual(result["count"], 2)
            self.assertEqual(len(result["packages"]), 2)
            self.assertEqual(result["packages"][0]["name"], "python3")
            
            # Verify the mock was called correctly
            mock_search.assert_called_once_with("python")

    def test_package_stats_resource(self):
        """Test the package_stats resource."""
        # Mock the get_package_stats method
        with patch.object(NixOSContext, 'get_package_stats') as mock_stats:
            mock_stats.return_value = {
                "aggregations": {
                    "channels": {"buckets": [{"key": "nixos-unstable", "doc_count": 80000}]},
                    "licenses": {"buckets": [{"key": "MIT", "doc_count": 20000}]},
                    "platforms": {"buckets": [{"key": "x86_64-linux", "doc_count": 70000}]}
                }
            }
            
            # Import the resource function
            from server import package_stats_resource
            
            # Call the resource function
            result = package_stats_resource()
            
            # Verify the result
            self.assertIn("aggregations", result)
            self.assertIn("channels", result["aggregations"])
            
            # Verify the mock was called
            mock_stats.assert_called_once()


if __name__ == "__main__":
    unittest.main()
