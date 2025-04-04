"""
Tests for the mcp_nixos package initialization.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import importlib


class TestPackageInit(unittest.TestCase):
    """Test the package initialization and version detection."""

    def setUp(self):
        """Set up test fixtures."""
        # Store the original module
        self.orig_module = sys.modules.get("mcp_nixos")
        # Make sure we use a fresh import for each test
        if "mcp_nixos" in sys.modules:
            del sys.modules["mcp_nixos"]

    def tearDown(self):
        """Tear down test fixtures."""
        # Restore the module after each test
        if self.orig_module:
            sys.modules["mcp_nixos"] = self.orig_module
        elif "mcp_nixos" in sys.modules:
            del sys.modules["mcp_nixos"]

    def test_version_from_importlib_metadata(self):
        """Test version detection using importlib.metadata."""
        with patch("importlib.metadata.version") as mock_version:
            # Setup the mock to return a specific version
            mock_version.return_value = "0.3.1"

            # Import the module to trigger version detection
            import mcp_nixos

            # Check that the version was set correctly
            self.assertEqual(mcp_nixos.__version__, "0.3.1")

            # Verify the mock was called correctly
            mock_version.assert_called_once_with("mcp-nixos")

    def test_version_from_importlib_metadata_package_not_found(self):
        """Test version fallback when package is not found."""
        with patch("importlib.metadata.version") as mock_version:
            # Setup the mock to raise PackageNotFoundError
            from importlib.metadata import PackageNotFoundError

            mock_version.side_effect = PackageNotFoundError("mcp-nixos")

            # Import the module to trigger version detection
            import mcp_nixos

            # Check that the fallback version was set
            self.assertEqual(mcp_nixos.__version__, "0.3.1")

    def test_version_from_pkg_resources(self):
        """Test version detection using pkg_resources fallback."""
        # First make sure importlib.metadata raises ImportError
        with patch("importlib.metadata.version", side_effect=ImportError):
            # Then mock pkg_resources
            mock_pkg_resources = MagicMock()
            mock_distribution = MagicMock()
            mock_distribution.version = "0.3.1"
            mock_pkg_resources.get_distribution.return_value = mock_distribution

            with patch.dict("sys.modules", {"pkg_resources": mock_pkg_resources}):
                # Import the module to trigger version detection
                import mcp_nixos

                # Check that the version was set correctly
                self.assertEqual(mcp_nixos.__version__, "0.3.1")

                # Verify the mock was called correctly
                mock_pkg_resources.get_distribution.assert_called_once_with("mcp-nixos")

    def test_version_fallback_when_all_methods_fail(self):
        """Test fallback to hardcoded version when all methods fail."""
        # First make sure importlib.metadata raises ImportError
        with patch("importlib.metadata.version", side_effect=ImportError):
            # Then mock pkg_resources to also fail
            mock_pkg_resources = MagicMock()
            mock_pkg_resources.get_distribution.side_effect = Exception("Resource not found")

            with patch.dict("sys.modules", {"pkg_resources": mock_pkg_resources}):
                # Import the module to trigger version detection
                import mcp_nixos

                # Check that the fallback version was set
                self.assertEqual(mcp_nixos.__version__, "0.3.1")


if __name__ == "__main__":
    unittest.main()
