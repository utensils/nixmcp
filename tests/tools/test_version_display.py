"""
Test to verify version information is properly displayed for real packages.
"""

import unittest
import pytest
from unittest.mock import patch
from mcp_nixos.contexts.nixos_context import NixOSContext
from mcp_nixos.tools.nixos_tools import nixos_info

# Mark as unit tests
pytestmark = pytest.mark.unit


class TestVersionDisplay(unittest.TestCase):
    """Test that version numbers are correctly displayed for real packages."""

    def test_real_package_version_display(self):
        """Test that version information is correctly displayed for an actual NixOS package."""
        # Use a mock context and package instead of making real API calls
        # This makes the test more reliable and not dependent on API availability
        package_name = "redis"

        # Create a mock context
        context = NixOSContext()

        # Create a mock package info that contains version
        mock_package_info = {
            "name": package_name,
            "version": "7.0.15",
            "description": "An open source, advanced key-value store",
            "homepage": "https://redis.io/",
            "license": "BSD-3-Clause",
            "found": True,
        }

        # Replace the get_package method to return our mock data
        with patch.object(NixOSContext, "get_package", return_value=mock_package_info):
            # Get the package info
            package_info = context.get_package(package_name)

            # Verify the version field exists
            self.assertIn("version", package_info)

            # Get the version value
            version = package_info.get("version", "")
            self.assertEqual(version, "7.0.15")

            # Now check the formatted output
            result = nixos_info(package_name, type="package", context=context)

            # Check that version is displayed in the output
            self.assertIn("**Version:**", result)

            # Version line should be displayed with the correct value
            version_string = f"**Version:** {version}"
            self.assertIn(version_string, result)

            # Also check for other important fields
            self.assertIn("**Description:**", result)
            self.assertIn("**Homepage:**", result)


if __name__ == "__main__":
    unittest.main()
