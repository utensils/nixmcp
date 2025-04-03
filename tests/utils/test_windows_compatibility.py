"""Tests for Windows-specific compatibility issues."""

import os
import sys
import pathlib
import tempfile
import shutil
import uuid
import pytest
from unittest import mock

# Mark as unit tests
pytestmark = pytest.mark.unit

from mcp_nixos.utils.cache_helpers import (
    get_default_cache_dir,
    ensure_cache_dir,
    init_cache_storage,
    lock_file,
    unlock_file,
    atomic_write,
)


class TestWindowsPathHandling:
    """Tests focused on Windows path handling compatibility."""

    def test_windows_cache_path_edge_cases(self):
        """Test Windows-specific path handling edge cases."""
        # Mock Windows platform
        with mock.patch("sys.platform", "win32"):
            # Test with empty LOCALAPPDATA
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": ""}, clear=True):
                with mock.patch("pathlib.Path.home", return_value=pathlib.Path("C:\\Users\\testuser")):
                    # Mock the home.exists() call to force the specific path generation
                    with mock.patch("pathlib.Path.exists", return_value=True):
                        cache_dir = get_default_cache_dir()
                        # Path separators can differ based on platform
                        # On Windows a normalized path would use \ but on macOS/Linux uses /
                        # Verify only the key components
                        norm_cache_lower = os.path.normcase(cache_dir).lower()
                        assert "testuser" in norm_cache_lower
                        assert "appdata" in norm_cache_lower
                        assert "local" in norm_cache_lower
                        assert "mcp_nixos" in norm_cache_lower
                        assert "cache" in norm_cache_lower

            # Test with path containing spaces
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": "C:\\Users\\Test User\\AppData\\Local"}):
                # Mock os.path.exists to ensure our mocked path is used
                with mock.patch("os.path.exists", return_value=True):
                    cache_dir = get_default_cache_dir()
                    # Use normcase to handle cross-platform path differences
                    norm_cache = os.path.normcase(cache_dir)
                    assert "test user" in norm_cache.lower()
                    assert "cache" in norm_cache.lower()

            # Test with Unicode characters
            with mock.patch.dict(os.environ, {"LOCALAPPDATA": "C:\\Users\\Тест\\AppData\\Local"}):
                # Mock os.path.exists to ensure our mocked path is used
                with mock.patch("os.path.exists", return_value=True):
                    cache_dir = get_default_cache_dir()
                    # The path should preserve the Unicode characters
                    assert "Тест" in cache_dir

    @pytest.mark.windows
    def test_real_windows_paths(self):
        """Test with the actual Windows environment (only runs on Windows)."""
        # This test only runs on Windows machines
        cache_dir = get_default_cache_dir("mcp_nixos_test")
        assert "mcp_nixos_test" in cache_dir
        assert "Cache" in cache_dir

        # Should be able to create the directory
        temp_cache_dir = os.path.join(tempfile.gettempdir(), f"mcp_nixos_test_{uuid.uuid4().hex}")
        try:
            actual_dir = ensure_cache_dir(temp_cache_dir)
            assert os.path.isdir(actual_dir)
            # On Windows, check paths with case-insensitive comparison
            assert os.path.normcase(actual_dir) == os.path.normcase(temp_cache_dir)
        except AssertionError as e:
            # Enhanced error reporting for Windows path issues
            print(f"Test failed with paths: \nactual_dir: {actual_dir} \ntemp_cache_dir: {temp_cache_dir}")
            raise e
        finally:
            # Clean up more safely with better error handling
            try:
                if os.path.exists(temp_cache_dir):
                    if os.path.isdir(temp_cache_dir):
                        # Use shutil.rmtree with ignore_errors for safer directory removal
                        shutil.rmtree(temp_cache_dir, ignore_errors=True)
                    else:
                        os.unlink(temp_cache_dir)
            except Exception as e:
                print(f"Warning: Failed to clean up temp directory {temp_cache_dir}: {str(e)}")


class TestWindowsFallbackCache:
    """Tests for cache fallback mechanisms on Windows."""

    def test_fallback_cache_creation(self):
        """Test that fallback cache creation works when the primary location fails."""
        # Mock a permission error when creating the directory
        with mock.patch("pathlib.Path.mkdir", side_effect=PermissionError("Access denied")):
            # Mock tempfile.mkdtemp to return a predictable path for testing
            test_temp_dir = os.path.join(tempfile.gettempdir(), f"mcp_nixos_temp_cache_{uuid.uuid4().hex}")
            with mock.patch("tempfile.mkdtemp", return_value=test_temp_dir):
                result = init_cache_storage(cache_dir="/path/that/cant/be/created")

                # Should return a valid configuration with initialized=False
                assert not result["initialized"]
                assert "error" in result
                assert "Access denied" in result["error"]
                assert result["cache_dir"] == test_temp_dir
                assert result["is_test_dir"] is True

    def test_multiple_fallback_attempts(self):
        """Test that multiple fallback attempts work correctly."""
        # Instead of mocking specific failures, just make sure the fallback mechanism works
        with mock.patch("pathlib.Path.mkdir", side_effect=PermissionError("Access denied")):
            # Create a real temporary directory for the test
            real_temp_dir = tempfile.mkdtemp(prefix="mcp_nixos_real_test_")
            try:
                with mock.patch("tempfile.mkdtemp", return_value=real_temp_dir):
                    # Initialize with a path that will fail
                    result = init_cache_storage(cache_dir="/bad/path")
                    # Check we got some fallback result
                    assert "cache_dir" in result
                    assert result["cache_dir"] == real_temp_dir
                    # The initialization failed but we still have a usable directory
                    assert not result["initialized"]
                    assert "error" in result
            finally:
                # Clean up
                if os.path.exists(real_temp_dir):
                    shutil.rmtree(real_temp_dir, ignore_errors=True)


class TestWindowsFileLocking:
    """Tests for Windows-specific file locking behavior."""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_windows_specific_file_operations(self, tmp_path):
        """Test Windows-specific file operations."""
        test_file = tmp_path / "windows_test.txt"

        # Test with a file path that would be valid on Windows but might cause issues
        special_file = tmp_path / "CON.txt"  # CON is a reserved name on Windows

        # We should handle this gracefully on real Windows systems
        # Write content safely even with a potentially problematic name
        content = "Test content for Windows compatibility"

        try:
            # This should succeed or fail gracefully
            atomic_write(special_file, lambda f: f.write(content))
        except Exception:
            # If it fails, that's expected - just make sure it doesn't crash
            pass

        # Regular files should always work
        assert atomic_write(test_file, lambda f: f.write(content))

        # Verify content
        with open(test_file, "r") as f:
            assert f.read() == content

    @pytest.mark.windows
    def test_windows_file_locking_on_windows(self, tmp_path):
        """Test file locking on real Windows systems."""
        test_file = tmp_path / "lock_test.txt"

        # Create test file with more robust error handling
        try:
            with open(test_file, "w") as f:
                f.write("Initial content")

            # On Windows, this should work without mocking
            with open(test_file, "r+") as f:
                # Should be able to acquire and release lock
                lock_result = lock_file(f, exclusive=True, blocking=True)
                assert lock_result, "Failed to acquire file lock on Windows"
                unlock_result = unlock_file(f)
                assert unlock_result, "Failed to release file lock on Windows"
        except Exception as e:
            # Provide better diagnostic information for Windows-specific errors
            pytest.fail(f"Windows file locking test failed: {e}")

        # Ensure file is properly closed before leaving the test
        import gc

        gc.collect()  # Force garbage collection to release any file handles

    def test_cross_platform_locking_simulation(self, tmp_path):
        """Test platform-agnostic locking behavior."""
        test_file = tmp_path / "lock_test.txt"

        # Create test file
        with open(test_file, "w") as f:
            f.write("Initial content")

        # This test works on all platforms
        with open(test_file, "r+") as f:
            # Import the underlying platform-specific functions that lock_file calls
            if sys.platform == "win32":
                module_name = "msvcrt"
                lock_function = "locking"
            else:
                module_name = "fcntl"
                lock_function = "flock"

            # Mock the underlying system call that lock_file would use
            with mock.patch(f"{module_name}.{lock_function}", return_value=None) as mock_sys_lock:
                # Call the lock functions - these should work across platforms
                assert lock_file(f, exclusive=True, blocking=True)
                assert unlock_file(f)

                # The underlying system function should be called
                assert mock_sys_lock.call_count > 0
