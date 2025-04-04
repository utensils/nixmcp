"""Tests for Home Manager client Windows compatibility."""

import os
import sys
import tempfile
import pytest
from unittest import mock
from pathlib import Path

from mcp_nixos.clients.home_manager_client import HomeManagerClient


# Mark as unit tests
pytestmark = pytest.mark.unit


class TestHomeManagerWindowsCompatibility:
    """Test Home Manager client Windows compatibility."""

    def test_windows_file_path_handling(self):
        """Test Windows-specific path handling in Home Manager client."""
        # Test with Windows platform
        with (
            mock.patch("sys.platform", "win32"),
            mock.patch.dict(os.environ, {"LOCALAPPDATA": r"C:\Users\testuser\AppData\Local"}),
        ):
            # Create a test directory
            test_dir = tempfile.mkdtemp(prefix="mcp_nixos_test_")
            try:
                # Override the actual cache directory to use our test directory
                with mock.patch("mcp_nixos.utils.cache_helpers.ensure_cache_dir", return_value=test_dir):
                    client = HomeManagerClient()

                    # Test loading from cache - should handle Windows paths correctly
                    # We'll create a mock cache file with some test data
                    cache_file = Path(test_dir) / "home_manager_options.json"
                    with open(cache_file, "w") as f:
                        f.write(
                            """
                        {
                            "timestamp": 1617235200,
                            "options": [
                                {
                                    "name": "programs.git.enable",
                                    "description": "Whether to enable Git.",
                                    "type": "boolean",
                                    "default": "false",
                                    "source": "options"
                                }
                            ]
                        }
                        """
                        )

                    # Load from cache - should handle Windows paths
                    client._load_from_cache()

                    # Verify options were loaded
                    assert len(client._options) > 0
                    assert client._options[0]["name"] == "programs.git.enable"
            finally:
                # Clean up
                import shutil

                shutil.rmtree(test_dir, ignore_errors=True)

    def test_windows_cache_write_operations(self):
        """Test cache write operations on Windows."""
        # Test with Windows platform
        with (
            mock.patch("sys.platform", "win32"),
            mock.patch.dict(os.environ, {"LOCALAPPDATA": r"C:\Users\testuser\AppData\Local"}),
        ):
            # Create a test directory
            test_dir = tempfile.mkdtemp(prefix="mcp_nixos_test_")
            try:
                # Override the actual cache directory to use our test directory
                with mock.patch("mcp_nixos.utils.cache_helpers.ensure_cache_dir", return_value=test_dir):
                    client = HomeManagerClient()

                    # Set up mock options
                    client._options = [
                        {
                            "name": "programs.git.enable",
                            "description": "Whether to enable Git.",
                            "type": "boolean",
                            "default": "false",
                            "source": "options",
                        }
                    ]

                    # Save to cache - should handle Windows paths
                    client._save_to_cache()

                    # Verify cache file was created
                    cache_file = Path(test_dir) / "home_manager_options.json"
                    assert os.path.exists(cache_file)

                    # Read back the cache to verify correct format
                    import json

                    with open(cache_file, "r") as f:
                        cache_data = json.load(f)

                    assert "timestamp" in cache_data
                    assert "options" in cache_data
                    assert len(cache_data["options"]) > 0
                    assert cache_data["options"][0]["name"] == "programs.git.enable"
            finally:
                # Clean up
                import shutil

                shutil.rmtree(test_dir, ignore_errors=True)

    def test_windows_file_locking_compatibility(self):
        """Test file locking compatibility on Windows."""
        # Skip on non-Windows platforms since we're using Windows-specific mocks
        if not sys.platform == "win32":
            # For non-Windows platforms, mock the platform to be Windows
            with mock.patch("sys.platform", "win32"):
                # Mock msvcrt which is used for Windows file locking
                with mock.patch("msvcrt.locking") as mock_locking:
                    # Create a test directory
                    test_dir = tempfile.mkdtemp(prefix="mcp_nixos_test_")
                    try:
                        # Override the actual cache directory to use our test directory
                        with mock.patch("mcp_nixos.utils.cache_helpers.ensure_cache_dir", return_value=test_dir):
                            client = HomeManagerClient()

                            # Set up mock options
                            client._options = [
                                {
                                    "name": "programs.git.enable",
                                    "description": "Whether to enable Git.",
                                    "type": "boolean",
                                    "default": "false",
                                    "source": "options",
                                }
                            ]

                            # Save to cache - should use Windows locking
                            client._save_to_cache()

                            # Verify Windows locking was used
                            assert mock_locking.call_count > 0
                    finally:
                        # Clean up
                        import shutil

                        shutil.rmtree(test_dir, ignore_errors=True)
        else:
            # On actual Windows, test real locking behavior
            # Create a test directory
            test_dir = tempfile.mkdtemp(prefix="mcp_nixos_test_")
            try:
                # Override the actual cache directory to use our test directory
                with mock.patch("mcp_nixos.utils.cache_helpers.ensure_cache_dir", return_value=test_dir):
                    client = HomeManagerClient()

                    # Set up mock options
                    client._options = [
                        {
                            "name": "programs.git.enable",
                            "description": "Whether to enable Git.",
                            "type": "boolean",
                            "default": "false",
                            "source": "options",
                        }
                    ]

                    # Save to cache - should work without errors on Windows
                    try:
                        client._save_to_cache()
                        # If we get here, locking worked
                        assert True
                    except Exception as e:
                        pytest.fail(f"Windows file locking failed: {e}")
            finally:
                # Clean up
                import shutil

                shutil.rmtree(test_dir, ignore_errors=True)

    def test_windows_path_normalization(self):
        """Test Windows path normalization."""
        # Test with Windows platform
        with mock.patch("sys.platform", "win32"):
            # Create paths with different casing/separators
            paths = [
                r"C:\Users\testuser\AppData\Local\mcp_nixos\Cache",
                r"c:\users\testuser\appdata\local\mcp_nixos\cache",
                r"C:/Users/testuser/AppData/Local/mcp_nixos/Cache",
            ]

            # Normalize all paths
            normalized_paths = [os.path.normcase(p) for p in paths]

            # All should be equivalent on Windows
            assert len(set(normalized_paths)) == 1, "Windows path normalization failed"


class TestHomeManagerURLHandlingCrossPlatform:
    """Test Home Manager URL handling across platforms."""

    def test_url_handling_cross_platform(self):
        """Test URL handling works the same across platforms."""
        # Test with different platforms
        platforms = ["win32", "darwin", "linux"]

        for platform in platforms:
            with mock.patch("sys.platform", platform):
                # Create a client
                client = HomeManagerClient()

                # Internal _fetch_url should work the same regardless of platform
                # Mock the fetch to avoid actual network requests
                with mock.patch.object(client._client, "fetch") as mock_fetch:
                    mock_fetch.return_value = "<html><body>Test</body></html>"

                    # Call fetch_url
                    client.fetch_url("https://example.com")

                    # URL should be passed unchanged regardless of platform
                    mock_fetch.assert_called_with("https://example.com", force_refresh=True)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
