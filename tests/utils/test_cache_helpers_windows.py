"""Tests for the Windows-specific functionality in cache_helpers.py."""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch, mock_open

from mcp_nixos.utils.cache_helpers import atomic_write


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
class TestWindowsAtomicWrite:
    """Test Windows-specific functionality in atomic_write."""

    def test_atomic_write_windows_replace(self):
        """Test atomic_write Windows file replacement."""
        # Create a mock temp file
        mock_temp_file = MagicMock()
        mock_temp_file.name = r"C:\temp\tempfile"

        # Mock lock_file to return True (lock succeeded)
        mock_lock_file = MagicMock(return_value=True)

        # Mock os.replace to raise an error
        mock_os_replace = MagicMock(side_effect=OSError("Access denied"))

        # Mock Windows-specific operations
        mock_windll = MagicMock()
        mock_kernel32 = MagicMock()
        mock_windll.kernel32 = mock_kernel32
        mock_kernel32.MoveFileExW.return_value = 1  # Indicates success

        # Mock file operations
        m = mock_open()

        # Create a mock tempfile module
        mock_tempfile_module = MagicMock()
        mock_tempfile_module.NamedTemporaryFile.return_value = mock_temp_file

        # First patch builtins.__import__ to control imports of tempfile
        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if name == "tempfile":
                return mock_tempfile_module
            return original_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=mock_import),
            patch("mcp_nixos.utils.cache_helpers.lock_file", mock_lock_file),
            patch("mcp_nixos.utils.cache_helpers.os.replace", mock_os_replace),
            patch("mcp_nixos.utils.cache_helpers.ctypes.windll", mock_windll),
            patch("mcp_nixos.utils.cache_helpers.os.path.exists", return_value=True),
            patch("builtins.open", m),
        ):
            # Call atomic_write
            result = atomic_write(r"C:\temp\target.txt", lambda f: f.write("test content"))
            assert result is True

            # Verify MoveFileExW was called
            mock_kernel32.MoveFileExW.assert_called_once()

    def test_atomic_write_windows_replace_failure(self):
        """Test atomic_write Windows file replacement failure."""
        # Create a mock temp file
        mock_temp_file = MagicMock()
        mock_temp_file.name = r"C:\temp\tempfile"

        # Mock lock_file to return True (lock succeeded)
        mock_lock_file = MagicMock(return_value=True)

        # Mock os.replace to raise an error
        mock_os_replace = MagicMock(side_effect=OSError("Access denied"))

        # Mock Windows-specific operations
        mock_windll = MagicMock()
        mock_kernel32 = MagicMock()
        mock_windll.kernel32 = mock_kernel32
        mock_kernel32.MoveFileExW.return_value = 0  # Indicates failure

        # Mock file operations
        m = mock_open()

        # Mock the logger
        mock_logger = MagicMock()

        # Create a mock tempfile module
        mock_tempfile_module = MagicMock()
        mock_tempfile_module.NamedTemporaryFile.return_value = mock_temp_file

        # First patch builtins.__import__ to control imports of tempfile
        original_import = __import__

        def mock_import(name, *args, **kwargs):
            if name == "tempfile":
                return mock_tempfile_module
            return original_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=mock_import),
            patch("mcp_nixos.utils.cache_helpers.lock_file", mock_lock_file),
            patch("mcp_nixos.utils.cache_helpers.os.replace", mock_os_replace),
            patch("mcp_nixos.utils.cache_helpers.ctypes.windll", mock_windll),
            patch("mcp_nixos.utils.cache_helpers.os.path.exists", return_value=True),
            patch("mcp_nixos.utils.cache_helpers.logger", mock_logger),
            patch("builtins.open", m),
        ):
            # Call atomic_write
            result = atomic_write(r"C:\temp\target.txt", lambda f: f.write("test content"))
            assert result is False

            # Verify error was logged
            mock_logger.error.assert_called_once()
