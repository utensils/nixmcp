"""
Tests for the mcp_nixos package initialization.
"""

import unittest
from unittest.mock import patch, MagicMock


class TestPackageInit(unittest.TestCase):
    """Test the package initialization and version detection."""

    def test_version_from_importlib_metadata(self):
        """Test version detection using importlib.metadata."""
        with patch("importlib.metadata.version") as mock_version:
            # Setup the mock to return a specific version
            mock_version.return_value = "0.3.1"
            
            # Re-import the module to trigger version detection
            with patch.dict("sys.modules", {"mcp_nixos": None}):
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
            
            # Re-import the module to trigger version detection
            with patch.dict("sys.modules", {"mcp_nixos": None}):
                import mcp_nixos
                
                # Check that the fallback version was set
                self.assertEqual(mcp_nixos.__version__, "0.3.1")

    def test_version_from_pkg_resources(self):
        """Test version detection using pkg_resources fallback."""
        # Mock ImportError for importlib.metadata
        with patch("importlib.metadata.version", side_effect=ImportError):
            # Mock pkg_resources
            mock_pkg_resources = MagicMock()
            mock_distribution = MagicMock()
            mock_distribution.version = "0.3.1"
            mock_pkg_resources.get_distribution.return_value = mock_distribution
            
            with patch.dict("sys.modules", {
                "mcp_nixos": None,
                "pkg_resources": mock_pkg_resources
            }):
                import mcp_nixos
                
                # Check that the version was set correctly
                self.assertEqual(mcp_nixos.__version__, "0.3.1")
                
                # Verify the mock was called correctly
                mock_pkg_resources.get_distribution.assert_called_once_with("mcp-nixos")

    def test_version_fallback_when_all_methods_fail(self):
        """Test fallback to hardcoded version when all methods fail."""
        # Mock ImportError for importlib.metadata
        with patch("importlib.metadata.version", side_effect=ImportError):
            # Mock Exception for pkg_resources
            mock_pkg_resources = MagicMock()
            mock_pkg_resources.get_distribution.side_effect = Exception("Resource not found")
            
            with patch.dict("sys.modules", {
                "mcp_nixos": None,
                "pkg_resources": mock_pkg_resources
            }):
                import mcp_nixos
                
                # Check that the fallback version was set
                self.assertEqual(mcp_nixos.__version__, "0.3.1")


if __name__ == "__main__":
    unittest.main()
