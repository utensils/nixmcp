"""
Tests for NixOS package documentation integration.
"""

import unittest
from unittest.mock import MagicMock, patch
from nixmcp.tools.nixos_tools import nixos_info
from nixmcp.contexts.nixos_context import NixOSContext


class TestNixOSPackageDocumentation(unittest.TestCase):
    """Test the NixOS package documentation integration."""

    def test_nixos_package_with_docs(self):
        """Test that NixOS package info displays version and documentation links."""
        # Create a mock context with the required methods
        mock_context = MagicMock()

        # Mock package data with all the fields we want to ensure are displayed
        mock_package_data = {
            "name": "redis",
            "pname": "redis",
            "version": "7.2.4",
            "description": "Open source, advanced key-value store",
            "longDescription": "Redis is an advanced key-value store...",
            "homepage": ["https://redis.io"],
            "license": [
                {
                    "url": "https://spdx.org/licenses/BSD-3-Clause.html",
                    "fullName": 'BSD 3-clause "New" or "Revised" License',
                }
            ],
            "position": "pkgs/servers/redis/default.nix:176",
            "programs": [
                "redis-check-rdb",
                "redis-benchmark",
                "redis-sentinel",
                "redis-check-aof",
                "redis-cli",
                "redis-server",
            ],
            "found": True,
        }

        # Set up the mock to return our package data
        mock_context.get_package.return_value = mock_package_data

        result = nixos_info("redis", type="package", context=mock_context)

        # Check for version and other important fields in the output
        self.assertIn("**Version:** 7.2.4", result)
        self.assertIn("**Homepage:** https://redis.io", result)
        self.assertIn('**License:** BSD 3-clause "New" or "Revised" License', result)
        self.assertIn("**Provided Programs:** redis-check-rdb, redis-benchmark", result)

        # Check for source code link as a Markdown link
        self.assertIn("**Source:** [pkgs/servers/redis/default.nix:176]", result)
        self.assertIn("https://github.com/NixOS/nixpkgs/blob/master/pkgs/servers/redis/default.nix#L176", result)


class TestRealNixOSPackageQueries(unittest.TestCase):
    """Integration tests for real NixOS package queries."""

    @patch("nixmcp.utils.helpers.make_http_request")
    def test_real_package_structure(self, mock_make_http_request):
        """Test that a real package query returns and formats all expected fields."""
        # Create a realistic Elasticsearch response
        mock_response = {
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "package_attr_name": "redis",
                            "package_pname": "redis",
                            "package_version": "7.2.4",
                            "package_description": "Open source, advanced key-value store",
                            "package_longDescription": "Redis is an advanced key-value store...",
                            "package_homepage": ["https://redis.io"],
                            "package_license": [
                                {
                                    "url": "https://spdx.org/licenses/BSD-3-Clause.html",
                                    "fullName": 'BSD 3-clause "New" or "Revised" License',
                                }
                            ],
                            "package_position": "pkgs/servers/redis/default.nix:176",
                            "package_maintainers": [
                                {"name": "maintainer1", "email": "m1@example.com"},
                                {"name": "maintainer2", "email": "m2@example.com"},
                            ],
                            "package_platforms": ["x86_64-linux", "aarch64-linux"],
                            "package_programs": [
                                "redis-check-rdb",
                                "redis-benchmark",
                                "redis-sentinel",
                                "redis-check-aof",
                                "redis-cli",
                                "redis-server",
                            ],
                        }
                    }
                ]
            }
        }

        # Mock the HTTP request to return our prepared response
        mock_make_http_request.return_value = mock_response

        # Create a real NixOS context
        context = NixOSContext()

        # Get package info
        package_info = context.get_package("redis")

        # Verify that all expected fields are present
        self.assertEqual(package_info["name"], "redis")
        self.assertEqual(package_info["version"], "7.2.4")
        self.assertIn("description", package_info)
        self.assertIn("longDescription", package_info)
        self.assertIn("homepage", package_info)
        self.assertIn("license", package_info)
        self.assertIn("position", package_info)
        self.assertIn("programs", package_info)
        self.assertTrue(package_info["found"])

        # Now check the formatted output
        result = nixos_info("redis", type="package", context=context)

        # Check for all expected sections in the formatted output
        self.assertIn("# redis", result)
        self.assertIn("**Version:** 7.2.4", result)
        self.assertIn("**Description:**", result)
        self.assertIn("**Homepage:**", result)
        self.assertIn("**License:**", result)
        self.assertIn("**Provided Programs:**", result)

        # The source link should be included as a formatted markdown link
        self.assertIn("**Source:** [pkgs/servers/redis/default.nix:176]", result)
        self.assertIn("https://github.com/NixOS/nixpkgs/blob/master/pkgs/servers/redis/default.nix#L176", result)
