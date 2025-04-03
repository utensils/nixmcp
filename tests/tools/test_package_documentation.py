"""
Tests for MCP-NixOS package documentation integration.
"""

import unittest
import pytest
from unittest.mock import MagicMock, patch

# Mark as unit tests
pytestmark = pytest.mark.unit

from mcp_nixos.tools.nixos_tools import nixos_info
from mcp_nixos.contexts.nixos_context import NixOSContext


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

        # Verify all programs are included, but don't test exact order since we sort them
        self.assertIn("**Provided Programs:**", result)
        for program in [
            "redis-check-rdb",
            "redis-benchmark",
            "redis-sentinel",
            "redis-check-aof",
            "redis-cli",
            "redis-server",
        ]:
            self.assertIn(program, result)

        # Check for source code link as a Markdown link
        self.assertIn("**Source:** [pkgs/servers/redis/default.nix:176]", result)
        self.assertIn("https://github.com/NixOS/nixpkgs/blob/master/pkgs/servers/redis/default.nix#L176", result)


class TestRealNixOSPackageQueries(unittest.TestCase):
    """Integration tests for real NixOS package queries."""

    @patch("mcp_nixos.contexts.nixos_context.NixOSContext.get_package")
    def test_real_package_structure(self, mock_get_package):
        """Test that a real package query returns and formats all expected fields."""
        # Create a mock package return value
        mock_package = {
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
            "maintainers": [
                {"name": "maintainer1", "email": "m1@example.com"},
                {"name": "maintainer2", "email": "m2@example.com"},
            ],
            "platforms": ["x86_64-linux", "aarch64-linux"],
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

        # Configure the mock to return our prepared package data
        mock_get_package.return_value = mock_package

        # Create a context
        context = NixOSContext()

        # Use the nixos_info tool directly with our mocked context
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
