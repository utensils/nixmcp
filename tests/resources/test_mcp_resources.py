import logging
from unittest.mock import patch
import pytest

# Mark as unit tests
pytestmark = pytest.mark.unit

# Import base test class
from tests import MCPNixOSTestBase

# Import for consistent test version
from mcp_nixos import __version__

# Import from the new modular structure
from mcp_nixos.contexts.nixos_context import NixOSContext
from mcp_nixos.resources.nixos_resources import (
    nixos_status_resource,
    package_resource,
    search_packages_resource,
    search_options_resource,
    option_resource,
    search_programs_resource,
    package_stats_resource,
)

# Disable logging during tests
logging.disable(logging.CRITICAL)


class TestMCPResourceEndpoints(MCPNixOSTestBase):
    """Test the MCP resource endpoints."""

    def test_status_resource_structure(self):
        """Test the structure of the status resource."""
        # Mock the get_status method
        with patch.object(NixOSContext, "get_status") as mock_status:
            mock_status.return_value = {
                "status": "ok",
                "version": __version__,
                "name": "MCP-NixOS",
                "description": "NixOS Model Context Protocol Server",
                "server_type": "http",
                "cache_stats": {
                    "size": 100,
                    "max_size": 500,
                    "ttl": 600,
                    "hits": 800,
                    "misses": 200,
                    "hit_ratio": 0.8,
                },
            }

            # Call the resource function
            result = nixos_status_resource(self.context)

            # Verify the structure of the response
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["version"], __version__)
            self.assertEqual(result["name"], "MCP-NixOS")
            self.assertIn("description", result)
            self.assertIn("cache_stats", result)

            # Verify the cache stats structure
            self.assertIn("size", result["cache_stats"])
            self.assertIn("max_size", result["cache_stats"])
            self.assertIn("hit_ratio", result["cache_stats"])

    def test_package_resource_found(self):
        """Test the package resource when a package is found."""
        # Mock the get_package method
        with patch.object(NixOSContext, "get_package") as mock_get:
            mock_get.return_value = {
                "name": "python3",
                "version": "3.10.12",
                "description": "Python programming language",
                "license": "MIT",
                "homepage": "https://www.python.org",
                "maintainers": ["Alice", "Bob"],
                "platforms": ["x86_64-linux", "aarch64-linux"],
                "found": True,
            }

            # Call the resource function
            result = package_resource("python3", self.context)

            # Verify the structure of the response
            self.assertEqual(result["name"], "python3")
            self.assertEqual(result["version"], "3.10.12")
            self.assertTrue(result["found"])
            self.assertEqual(result["license"], "MIT")
            self.assertEqual(result["homepage"], "https://www.python.org")
            self.assertEqual(result["maintainers"], ["Alice", "Bob"])
            self.assertEqual(result["platforms"], ["x86_64-linux", "aarch64-linux"])

    def test_package_resource_not_found(self):
        """Test the package resource when a package is not found."""
        # Mock the get_package method
        with patch.object(NixOSContext, "get_package") as mock_get:
            mock_get.return_value = {
                "name": "nonexistent-package",
                "error": "Package not found",
                "found": False,
            }

            # Call the resource function
            result = package_resource("nonexistent-package", self.context)

            # Verify the structure of the response
            self.assertEqual(result["name"], "nonexistent-package")
            self.assertFalse(result["found"])
            self.assertEqual(result["error"], "Package not found")

    def test_search_packages_resource(self):
        """Test the search_packages resource."""
        # Mock the search_packages method
        with patch.object(NixOSContext, "search_packages") as mock_search:
            mock_search.return_value = {
                "count": 2,
                "packages": [
                    {
                        "name": "python3",
                        "version": "3.10.12",
                        "description": "Python programming language",
                    },
                    {
                        "name": "python39",
                        "version": "3.9.18",
                        "description": "Python 3.9",
                    },
                ],
            }

            # Call the resource function
            result = search_packages_resource("python", self.context)

            # Verify the structure of the response
            self.assertEqual(result["count"], 2)
            self.assertEqual(len(result["packages"]), 2)
            self.assertEqual(result["packages"][0]["name"], "python3")
            self.assertEqual(result["packages"][1]["name"], "python39")

            # Verify the mock was called correctly
            mock_search.assert_called_once_with("python")

    def test_search_options_resource(self):
        """Test the search_options resource."""
        # Mock the search_options method
        with patch.object(NixOSContext, "search_options") as mock_search:
            mock_search.return_value = {
                "count": 2,
                "options": [
                    {
                        "name": "services.nginx.enable",
                        "description": "Whether to enable nginx.",
                        "type": "boolean",
                        "default": "false",
                    },
                    {
                        "name": "services.nginx.virtualHosts",
                        "description": "Declarative vhost config",
                        "type": "attribute set",
                        "default": "{}",
                    },
                ],
            }

            # Call the resource function
            result = search_options_resource("nginx", self.context)

            # Verify the structure of the response
            self.assertEqual(result["count"], 2)
            self.assertEqual(len(result["options"]), 2)
            self.assertEqual(result["options"][0]["name"], "services.nginx.enable")
            self.assertEqual(result["options"][1]["name"], "services.nginx.virtualHosts")

            # Verify the mock was called correctly
            mock_search.assert_called_once_with("nginx")

    def test_option_resource(self):
        """Test the option resource."""
        # Mock the get_option method
        with patch.object(NixOSContext, "get_option") as mock_get:
            mock_get.return_value = {
                "name": "services.nginx.enable",
                "description": "Whether to enable nginx.",
                "type": "boolean",
                "default": "false",
                "example": "true",
                "declarations": ["/nix/store/...-nixos/modules/services/web-servers/nginx/default.nix"],
                "readOnly": False,
                "found": True,
            }

            # Call the resource function
            result = option_resource("services.nginx.enable", self.context)

            # Verify the structure of the response
            self.assertEqual(result["name"], "services.nginx.enable")
            self.assertEqual(result["type"], "boolean")
            self.assertEqual(result["default"], "false")
            self.assertTrue(result["found"])
            self.assertEqual(result["example"], "true")
            self.assertEqual(
                result["declarations"],
                ["/nix/store/...-nixos/modules/services/web-servers/nginx/default.nix"],
            )
            self.assertFalse(result["readOnly"])

    def test_search_programs_resource(self):
        """Test the search_programs resource."""
        # Mock the search_programs method
        with patch.object(NixOSContext, "search_programs") as mock_search:
            mock_search.return_value = {
                "count": 2,
                "packages": [
                    {
                        "name": "python3",
                        "programs": ["python3", "python3.10"],
                        "description": "Python programming language",
                    },
                    {
                        "name": "python39",
                        "programs": ["python3.9"],
                        "description": "Python 3.9",
                    },
                ],
            }

            # Call the resource function
            result = search_programs_resource("python", self.context)

            # Verify the structure of the response
            self.assertEqual(result["count"], 2)
            self.assertEqual(len(result["packages"]), 2)
            self.assertEqual(result["packages"][0]["name"], "python3")
            self.assertEqual(result["packages"][0]["programs"], ["python3", "python3.10"])

            # Verify the mock was called correctly
            mock_search.assert_called_once_with("python")

    def test_package_stats_resource(self):
        """Test the package_stats resource."""
        # Mock the get_package_stats method
        with patch.object(NixOSContext, "get_package_stats") as mock_stats:
            mock_stats.return_value = {
                "aggregations": {
                    "channels": {
                        "buckets": [
                            {"key": "nixos-unstable", "doc_count": 80000},
                            {"key": "nixos-23.11", "doc_count": 75000},
                        ]
                    },
                    "licenses": {
                        "buckets": [
                            {"key": "MIT", "doc_count": 20000},
                            {"key": "GPL", "doc_count": 15000},
                        ]
                    },
                    "platforms": {
                        "buckets": [
                            {"key": "x86_64-linux", "doc_count": 70000},
                            {"key": "aarch64-linux", "doc_count": 60000},
                        ]
                    },
                }
            }

            # Call the resource function
            result = package_stats_resource(self.context)

            # Verify the structure of the response
            self.assertIn("aggregations", result)
            self.assertIn("channels", result["aggregations"])
            self.assertIn("licenses", result["aggregations"])
            self.assertIn("platforms", result["aggregations"])

            # Verify the mock was called correctly
            mock_stats.assert_called_once()


if __name__ == "__main__":
    import unittest

    unittest.main()
