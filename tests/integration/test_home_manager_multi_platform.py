"""Integration tests for Home Manager cross-platform compatibility."""

import os
import sys
import tempfile
import pytest
import json
import pathlib
from unittest import mock

from mcp_nixos.clients.home_manager_client import HomeManagerClient
from mcp_nixos.contexts.home_manager_context import HomeManagerContext
from mcp_nixos.tools.home_manager_tools import home_manager_search, home_manager_info


# Mark as integration tests
pytestmark = pytest.mark.integration


class TestHomeManagerMultiPlatformIntegration:
    """Integration tests for Home Manager cross-platform compatibility."""

    def setup_method(self):
        """Set up test environment."""
        # Create a temporary cache directory
        self.test_cache_dir = tempfile.mkdtemp(prefix="mcp_nixos_test_")
        
        # Set up mock options for testing
        self.mock_options = [
            {
                "name": "programs.git.enable",
                "description": "Whether to enable Git.",
                "type": "boolean",
                "default": "false",
                "source": "options"
            },
            {
                "name": "programs.firefox.enable",
                "description": "Whether to enable Firefox.",
                "type": "boolean",
                "default": "false",
                "source": "options"
            },
            {
                "name": "services.syncthing.enable",
                "description": "Whether to enable Syncthing service.",
                "type": "boolean",
                "default": "false",
                "source": "options"
            }
        ]

    def teardown_method(self):
        """Clean up after each test."""
        import shutil
        shutil.rmtree(self.test_cache_dir, ignore_errors=True)

    def test_platform_agnostic_file_loading(self):
        """Test that file loading works across platforms."""
        # Test with mocked platform detection
        for platform in ["linux", "darwin", "win32"]:
            with mock.patch("sys.platform", platform):
                # Create a cache file with mock data
                if platform == "win32":
                    cache_subdir = os.path.join(self.test_cache_dir, "windows")
                elif platform == "darwin":
                    cache_subdir = os.path.join(self.test_cache_dir, "macos")
                else:
                    cache_subdir = os.path.join(self.test_cache_dir, "linux")
                
                os.makedirs(cache_subdir, exist_ok=True)
                
                cache_file = os.path.join(cache_subdir, "home_manager_options.json")
                with open(cache_file, "w") as f:
                    json.dump({
                        "timestamp": 1617235200,
                        "options": self.mock_options
                    }, f)
                
                # Create client with our test cache dir
                with mock.patch("mcp_nixos.utils.cache_helpers.ensure_cache_dir", return_value=cache_subdir):
                    client = HomeManagerClient()
                    
                    # Load from cache - should work the same on all platforms
                    client._load_from_cache()
                    
                    # Verify options were loaded
                    assert len(client._options) == 3
                    assert client._options[0]["name"] == "programs.git.enable"

    def test_search_tool_cross_platform(self):
        """Test that the home_manager_search tool works across platforms."""
        # Create a context for testing
        context = HomeManagerContext()
        
        # Mock client to return mock options
        mock_client = mock.MagicMock()
        mock_client.search_options.return_value = self.mock_options
        
        # Set loaded state and mock client
        context._client = mock_client
        context._state = "loaded"
        
        # Test with simulated different platforms
        for platform in ["linux", "darwin", "win32"]:
            with mock.patch("sys.platform", platform):
                # Run search - should work the same on all platforms
                result = home_manager_search(query="git", context=context)
                
                # Verify results contain the expected option
                assert "programs.git.enable" in result

    def test_info_tool_cross_platform(self):
        """Test that the home_manager_info tool works across platforms."""
        # Create a context for testing
        context = HomeManagerContext()
        
        # Mock client to return mock option
        mock_client = mock.MagicMock()
        mock_client.get_option.return_value = self.mock_options[0]
        
        # Set loaded state and mock client
        context._client = mock_client
        context._state = "loaded"
        
        # Test with simulated different platforms
        for platform in ["linux", "darwin", "win32"]:
            with mock.patch("sys.platform", platform):
                # Run info - should work the same on all platforms
                result = home_manager_info(name="programs.git.enable", context=context)
                
                # Verify results contain the expected info
                assert "programs.git.enable" in result
                assert "Whether to enable Git" in result

    def test_state_persistence_cross_platform(self):
        """Test that client state persists correctly across platforms."""
        # Test with mocked platform detection
        for platform in ["linux", "darwin", "win32"]:
            with mock.patch("sys.platform", platform):
                # Create a cache file path specific to the platform
                if platform == "win32":
                    cache_subdir = os.path.join(self.test_cache_dir, "windows")
                elif platform == "darwin":
                    cache_subdir = os.path.join(self.test_cache_dir, "macos")
                else:
                    cache_subdir = os.path.join(self.test_cache_dir, "linux")
                
                os.makedirs(cache_subdir, exist_ok=True)
                
                # Create client with our test cache dir
                with mock.patch("mcp_nixos.utils.cache_helpers.ensure_cache_dir", return_value=cache_subdir):
                    client = HomeManagerClient()
                    
                    # Set mock options
                    client._options = self.mock_options
                    
                    # Save to cache - should work on all platforms
                    client._save_to_cache()
                    
                    # Verify cache file was created
                    cache_file = os.path.join(cache_subdir, "home_manager_options.json")
                    assert os.path.exists(cache_file)
                    
                    # Create a new client instance
                    new_client = HomeManagerClient()
                    
                    # Load from cache - should find the file we just wrote
                    new_client._load_from_cache()
                    
                    # Verify options were loaded from cache
                    assert len(new_client._options) == 3
                    assert new_client._options[0]["name"] == "programs.git.enable"


class TestHomeManagetClientStringNormalization:
    """Test string normalization behavior to ensure cross-platform consistency."""

    def test_consistent_string_handling(self):
        """Test that string handling is consistent across platforms."""
        # Create a client
        client = HomeManagerClient()
        
        # Sample options with various string formats
        options = [
            {
                "name": "programs.git.enable",
                "description": "Line ending test.\r\nWindows line ending.",
                "type": "boolean",
                "default": "false",
                "source": "options"
            },
            {
                "name": "programs.firefox.enable",
                "description": "Line ending test.\nUnix line ending.",
                "type": "boolean",
                "default": "false",
                "source": "options"
            },
            {
                "name": "services.syncthing.enable",
                "description": "Unicode test: ñáéíóú 你好.",
                "type": "boolean",
                "default": "false",
                "source": "options"
            }
        ]
        
        # Set client options
        client._options = options
        
        # Build search indices
        client._build_search_indices()
        
        # Search should work the same regardless of line endings or Unicode
        results_windows = client.search_options("Windows line ending")
        results_unix = client.search_options("Unix line ending")
        results_unicode = client.search_options("Unicode test")
        
        # Verify all searches return results
        assert len(results_windows) > 0
        assert len(results_unix) > 0
        assert len(results_unicode) > 0
        
        # Verify correct options found
        assert results_windows[0]["name"] == "programs.git.enable"
        assert results_unix[0]["name"] == "programs.firefox.enable"
        assert results_unicode[0]["name"] == "services.syncthing.enable"


if __name__ == "__main__":
    pytest.main(["-v", __file__])