"""Unit tests for cache directory management utilities."""

import os
import sys
import tempfile
import pathlib
from unittest import mock

import pytest

# Mark as unit tests
pytestmark = pytest.mark.unit

from mcp_nixos.utils.cache_helpers import (
    get_default_cache_dir,
    ensure_cache_dir,
    init_cache_storage,
)


class TestCacheHelpers:
    """Tests for the cache directory management utilities."""

    def test_get_default_cache_dir_linux(self):
        """Test default cache directory paths on Linux."""
        with mock.patch("sys.platform", "linux"):
            # Test with XDG_CACHE_HOME set
            with mock.patch.dict(os.environ, {"XDG_CACHE_HOME": "/xdg/cache"}):
                cache_dir = get_default_cache_dir()
                # Use os.path.normpath for platform-agnostic path comparison
                expected = os.path.normpath("/xdg/cache/mcp_nixos")
                assert os.path.normpath(cache_dir) == expected

            # Test without XDG_CACHE_HOME (fallback to ~/.cache)
            with mock.patch.dict(os.environ, {}, clear=True):
                with mock.patch("pathlib.Path.home", return_value=pathlib.Path("/home/user")):
                    cache_dir = get_default_cache_dir()
                    expected = os.path.normpath("/home/user/.cache/mcp_nixos")
                    assert os.path.normpath(cache_dir) == expected

    def test_get_default_cache_dir_macos(self):
        """Test default cache directory paths on macOS."""
        with mock.patch("sys.platform", "darwin"):
            with mock.patch("pathlib.Path.home", return_value=pathlib.Path("/Users/user")):
                cache_dir = get_default_cache_dir()
                expected = os.path.normpath("/Users/user/Library/Caches/mcp_nixos")
                assert os.path.normpath(cache_dir) == expected

    def test_get_default_cache_dir_windows(self):
        """Test default cache directory paths on Windows."""
        with mock.patch("sys.platform", "win32"):
            # Test with LOCALAPPDATA set
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": "C:\\Users\\user\\AppData\\Local"}):
                # We need to also mock the existence check for the path
                with mock.patch("os.path.exists", return_value=True):
                    cache_dir = get_default_cache_dir()
                    expected = os.path.join("C:\\Users\\user\\AppData\\Local", "mcp_nixos", "Cache")
                    # Use normcase for cross-platform path comparison
                    assert os.path.normcase(cache_dir) == os.path.normcase(expected)

            # Test without LOCALAPPDATA (fallback)
            with mock.patch.dict(os.environ, {}, clear=True):
                with mock.patch("pathlib.Path.home", return_value=pathlib.Path("C:\\Users\\user")):
                    # Mock the home.exists() call
                    with mock.patch("pathlib.Path.exists", return_value=True):
                        cache_dir = get_default_cache_dir()
                        expected = os.path.join("C:\\Users\\user", "AppData", "Local", "mcp_nixos", "Cache")
                        # Use normcase for cross-platform path comparison
                        assert os.path.normcase(cache_dir) == os.path.normcase(expected)

    def test_get_default_cache_dir_unsupported(self):
        """Test fallback for unsupported platforms."""
        with mock.patch("sys.platform", "unknown"):
            with mock.patch("pathlib.Path.home", return_value=pathlib.Path("/home/user")):
                cache_dir = get_default_cache_dir()
                expected = os.path.normpath("/home/user/.cache/mcp_nixos")
                assert os.path.normpath(cache_dir) == expected

    def test_get_default_cache_dir_custom_app_name(self):
        """Test custom app name for cache directory."""
        with mock.patch("sys.platform", "linux"):
            with mock.patch("pathlib.Path.home", return_value=pathlib.Path("/home/user")):
                cache_dir = get_default_cache_dir(app_name="custom_app")
                expected = os.path.normpath("/home/user/.cache/custom_app")
                assert os.path.normpath(cache_dir) == expected

    def test_ensure_cache_dir_explicit_path(self):
        """Test ensuring cache directory with explicit path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = os.path.join(temp_dir, "test_cache")
            result = ensure_cache_dir(test_dir)
            assert result == test_dir
            assert os.path.exists(test_dir)

    def test_ensure_cache_dir_env_var(self):
        """Test ensuring cache directory using environment variable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            env_dir = os.path.join(temp_dir, "env_cache")
            with mock.patch.dict(os.environ, {"MCP_NIXOS_CACHE_DIR": env_dir}):
                result = ensure_cache_dir()
                assert result == env_dir
                assert os.path.exists(env_dir)

    def test_ensure_cache_dir_default(self):
        """Test ensuring cache directory using default location."""
        # Save original env var value
        original_cache_dir = os.environ.get("MCP_NIXOS_CACHE_DIR")

        try:
            # Temporarily clear the env var to test default path behavior
            if "MCP_NIXOS_CACHE_DIR" in os.environ:
                del os.environ["MCP_NIXOS_CACHE_DIR"]

            with mock.patch("mcp_nixos.utils.cache_helpers.get_default_cache_dir") as mock_default:
                with tempfile.TemporaryDirectory() as temp_dir:
                    mock_default.return_value = temp_dir
                    result = ensure_cache_dir()
                    assert result == temp_dir
        finally:
            # Restore original env var if it existed
            if original_cache_dir is not None:
                os.environ["MCP_NIXOS_CACHE_DIR"] = original_cache_dir

    def test_ensure_cache_dir_error(self):
        """Test error handling when directory creation fails."""
        if sys.platform == "win32":
            # Windows has different permission model, skip this test
            pytest.skip("Test not applicable on Windows")

        # Try to create dir in a location we don't have permission for
        with mock.patch("pathlib.Path.mkdir", side_effect=PermissionError("Permission denied")):
            with pytest.raises(OSError):
                ensure_cache_dir("/tmp/no_perm_dir")

    def test_init_cache_storage_success(self):
        """Test successful cache storage initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = init_cache_storage(temp_dir, ttl=3600)
            assert result["cache_dir"] == temp_dir
            assert result["ttl"] == 3600
            assert result["initialized"] is True

    def test_init_cache_storage_fallback(self):
        """Test fallback when cache initialization fails."""
        with mock.patch(
            "mcp_nixos.utils.cache_helpers.ensure_cache_dir", side_effect=OSError("Failed to create directory")
        ):
            result = init_cache_storage()
            assert "initialized" in result
            assert result["initialized"] is False
            assert "error" in result
            # It should fall back to a temp directory
            assert os.path.exists(result["cache_dir"])
