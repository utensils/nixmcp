"""
Test to verify version information is properly displayed for real packages.
"""

import unittest
from nixmcp.contexts.nixos_context import NixOSContext
from nixmcp.tools.nixos_tools import nixos_info


class TestVersionDisplay(unittest.TestCase):
    """Test that version numbers are correctly displayed for real packages."""

    def test_real_package_version_display(self):
        """Test that version information is correctly displayed for an actual NixOS package."""
        # Use redis as our test package
        package_name = "redis"

        # Create a real context (this will make actual API calls)
        # Note: This is an integration test that requires internet access
        context = NixOSContext()

        # Print the debug message to fetch package
        print(f"\nFetching package info for '{package_name}'...")

        # Get the package info
        package_info = context.get_package(package_name)

        # Print raw package info for debugging
        print(f"Raw package info: {package_info}")

        # Verify the version field exists
        self.assertIn("version", package_info)

        # Print the version value for debugging
        version = package_info.get("version", "")
        print(f"Version value: '{version}'")

        # Now check the formatted output
        result = nixos_info(package_name, type="package", context=context)

        # Print a snippet of the output
        print(f"Result snippet: {result[:200]}...")

        # Check that version is displayed in the output
        self.assertIn("**Version:**", result)

        # Version line should be displayed regardless of content
        if version:
            # If version is available, it should be displayed
            version_string = f"**Version:** {version}"
            self.assertIn(version_string, result)
        else:
            # If version is not available, a user-friendly message should be displayed
            self.assertIn("**Version:** Not available", result)

        # Also check for other important fields
        self.assertIn("**Description:**", result)
        self.assertIn("**Homepage:**", result)


if __name__ == "__main__":
    unittest.main()
