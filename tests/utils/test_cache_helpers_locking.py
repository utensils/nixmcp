"""Tests for the cache_helpers.py module focusing on file locking mechanisms."""

import os
import pytest
import tempfile
from unittest.mock import MagicMock, patch, mock_open

from mcp_nixos.utils.cache_helpers import lock_file, unlock_file, atomic_write, write_with_metadata, read_with_metadata


class TestFileLocking:
    """Test the file locking mechanisms in cache_helpers."""
    
    def test_lock_file_closed_handle(self):
        """Test lock_file with a closed file handle."""
        # Create a mock file that is closed
        mock_file = MagicMock()
        mock_file.closed = True
        
        # Should return False for a closed file
        result = lock_file(mock_file)
        assert result is False
    
    @pytest.mark.skipif(os.name != 'posix', reason="Unix-specific test")
    def test_unix_lock_file_eacces_error(self):
        """Test lock_file on Unix with EACCES error."""
        # Create a mock file that is not closed
        mock_file = MagicMock()
        mock_file.closed = False
        
        # Mock fcntl.flock to raise an error with errno.EACCES
        mock_fcntl = MagicMock()
        mock_fcntl.flock.side_effect = OSError()
        mock_fcntl.LOCK_EX = 2
        mock_fcntl.LOCK_NB = 4
        
        # Set up mock error with a specific errno
        mock_error = OSError()
        mock_error.errno = 13  # EACCES
        
        with patch('mcp_nixos.utils.cache_helpers.fcntl', mock_fcntl), \
             patch('mcp_nixos.utils.cache_helpers.errno.EACCES', 13), \
             patch('mcp_nixos.utils.cache_helpers.errno.EAGAIN', 11), \
             patch('mcp_nixos.utils.cache_helpers.time.sleep'), \
             patch('mcp_nixos.utils.cache_helpers.fcntl.flock', side_effect=mock_error):
            
            # Should return False due to the EACCES error
            result = lock_file(mock_file, timeout=0.1)
            assert result is False
    
    @pytest.mark.skipif(os.name != 'posix', reason="Unix-specific test")
    def test_unix_lock_file_eagain_error(self):
        """Test lock_file on Unix with EAGAIN error."""
        # Create a mock file that is not closed
        mock_file = MagicMock()
        mock_file.closed = False
        
        # Mock fcntl.flock to raise an error with errno.EAGAIN
        mock_fcntl = MagicMock()
        mock_fcntl.flock.side_effect = OSError()
        mock_fcntl.LOCK_EX = 2
        mock_fcntl.LOCK_NB = 4
        
        # Set up mock error with a specific errno
        mock_error = OSError()
        mock_error.errno = 11  # EAGAIN
        
        with patch('mcp_nixos.utils.cache_helpers.fcntl', mock_fcntl), \
             patch('mcp_nixos.utils.cache_helpers.errno.EACCES', 13), \
             patch('mcp_nixos.utils.cache_helpers.errno.EAGAIN', 11), \
             patch('mcp_nixos.utils.cache_helpers.time.sleep'), \
             patch('mcp_nixos.utils.cache_helpers.fcntl.flock', side_effect=mock_error):
            
            # Should return False due to the EAGAIN error
            result = lock_file(mock_file, timeout=0.1)
            assert result is False
    
    @pytest.mark.skipif(os.name != 'posix', reason="Unix-specific test")
    def test_unix_lock_file_other_error(self):
        """Test lock_file on Unix with a different error."""
        # Create a mock file that is not closed
        mock_file = MagicMock()
        mock_file.closed = False
        
        # Mock fcntl.flock to raise an error with a different errno
        mock_fcntl = MagicMock()
        mock_fcntl.flock.side_effect = OSError()
        mock_fcntl.LOCK_EX = 2
        mock_fcntl.LOCK_NB = 4
        
        # Set up mock error with a specific errno
        mock_error = OSError()
        mock_error.errno = 5  # Something else
        
        with patch('mcp_nixos.utils.cache_helpers.fcntl', mock_fcntl), \
             patch('mcp_nixos.utils.cache_helpers.errno.EACCES', 13), \
             patch('mcp_nixos.utils.cache_helpers.errno.EAGAIN', 11), \
             patch('mcp_nixos.utils.cache_helpers.fcntl.flock', side_effect=mock_error):
            
            # Should raise the original error
            with pytest.raises(OSError):
                lock_file(mock_file, timeout=0.1)
    
    @pytest.mark.skipif(os.name != 'posix', reason="Unix-specific test")
    def test_unix_lock_file_unlimited_timeout(self):
        """Test lock_file on Unix with an unlimited timeout."""
        # Create a mock file that is not closed
        mock_file = MagicMock()
        mock_file.closed = False
        
        # Mock fcntl.flock for blocking mode
        mock_fcntl = MagicMock()
        mock_fcntl.LOCK_EX = 2
        
        with patch('mcp_nixos.utils.cache_helpers.fcntl', mock_fcntl), \
             patch('mcp_nixos.utils.cache_helpers.fcntl.flock'):
            
            # Should return True for a successful lock with None timeout
            result = lock_file(mock_file, timeout=None)
            assert result is True
            # Should have used LOCK_EX without LOCK_NB
            mock_fcntl.flock.assert_called_once_with(mock_file, mock_fcntl.LOCK_EX)
    
    def test_unlock_file_windows(self):
        """Test unlock_file on Windows."""
        # Skip the test if not on Windows
        if os.name != 'nt':
            pytest.skip("Windows-specific test")
        
        # Create a mock file
        mock_file = MagicMock()
        mock_file.closed = False
        
        # Mock msvcrt.locking
        mock_msvcrt = MagicMock()
        mock_msvcrt.LK_UNLCK = 0
        
        with patch('mcp_nixos.utils.cache_helpers.msvcrt', mock_msvcrt), \
             patch('mcp_nixos.utils.cache_helpers.os.lseek'):
            
            # Call the function
            unlock_file(mock_file)
            
            # Check that msvcrt.locking was called
            mock_msvcrt.locking.assert_called_once()
    
    def test_unlock_file_error(self):
        """Test unlock_file with an error."""
        # Create a mock file
        mock_file = MagicMock()
        mock_file.closed = False
        
        # Mock platform-specific details
        if os.name == 'nt':
            # For Windows, mock msvcrt.locking to raise an error
            mock_msvcrt = MagicMock()
            mock_msvcrt.locking.side_effect = IOError("Unlock failed")
            module_to_patch = 'mcp_nixos.utils.cache_helpers.msvcrt'
            mock_module = mock_msvcrt
        else:
            # For Unix, mock fcntl.flock to raise an error
            mock_fcntl = MagicMock()
            mock_fcntl.flock.side_effect = IOError("Unlock failed")
            mock_fcntl.LOCK_UN = 8
            module_to_patch = 'mcp_nixos.utils.cache_helpers.fcntl'
            mock_module = mock_fcntl
        
        # Mock the logger
        mock_logger = MagicMock()
        
        with patch(module_to_patch, mock_module), \
             patch('mcp_nixos.utils.cache_helpers.logger', mock_logger):
            
            # Call the function - should not raise an error but log it
            unlock_file(mock_file)
            
            # Check that an error was logged
            mock_logger.debug.assert_called_once()
            assert "Error unlocking file" in mock_logger.debug.call_args[0][0]


class TestAtomicWrite:
    """Test the atomic_write function in cache_helpers."""
    
    def test_atomic_write_lock_failed(self):
        """Test atomic_write when lock acquisition fails."""
        # Create a mock temp file
        mock_temp_file = MagicMock()
        mock_temp_file.name = "/tmp/tempfile"
        
        # Mock NamedTemporaryFile to return our mock
        mock_named_temp = MagicMock(return_value=mock_temp_file)
        
        # Mock lock_file to return False (lock failed)
        mock_lock_file = MagicMock(return_value=False)
        
        # Mock os.replace
        mock_os_replace = MagicMock()
        
        # Mock file operations
        m = mock_open()
        
        with patch('mcp_nixos.utils.cache_helpers.tempfile.NamedTemporaryFile', mock_named_temp), \
             patch('mcp_nixos.utils.cache_helpers.lock_file', mock_lock_file), \
             patch('mcp_nixos.utils.cache_helpers.os.replace', mock_os_replace), \
             patch('builtins.open', m):
            
            # Call atomic_write - should not raise an error but return False
            result = atomic_write("/tmp/target.txt", "test content")
            assert result is False
            
            # Verify no replace was called
            mock_os_replace.assert_not_called()
    
    def test_atomic_write_windows_replace(self):
        """Test atomic_write Windows file replacement."""
        # Skip the test if not on Windows
        if os.name != 'nt':
            pytest.skip("Windows-specific test")
        
        # Create a mock temp file
        mock_temp_file = MagicMock()
        mock_temp_file.name = r"C:\temp\tempfile"
        
        # Mock NamedTemporaryFile to return our mock
        mock_named_temp = MagicMock(return_value=mock_temp_file)
        
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
        
        with patch('mcp_nixos.utils.cache_helpers.tempfile.NamedTemporaryFile', mock_named_temp), \
             patch('mcp_nixos.utils.cache_helpers.lock_file', mock_lock_file), \
             patch('mcp_nixos.utils.cache_helpers.os.replace', mock_os_replace), \
             patch('mcp_nixos.utils.cache_helpers.ctypes.windll', mock_windll), \
             patch('mcp_nixos.utils.cache_helpers.os.path.exists', return_value=True), \
             patch('builtins.open', m):
            
            # Call atomic_write
            result = atomic_write(r"C:\temp\target.txt", "test content")
            assert result is True
            
            # Verify MoveFileExW was called
            mock_kernel32.MoveFileExW.assert_called_once()
    
    def test_atomic_write_windows_replace_failure(self):
        """Test atomic_write Windows file replacement failure."""
        # Skip the test if not on Windows
        if os.name != 'nt':
            pytest.skip("Windows-specific test")
        
        # Create a mock temp file
        mock_temp_file = MagicMock()
        mock_temp_file.name = r"C:\temp\tempfile"
        
        # Mock NamedTemporaryFile to return our mock
        mock_named_temp = MagicMock(return_value=mock_temp_file)
        
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
        
        with patch('mcp_nixos.utils.cache_helpers.tempfile.NamedTemporaryFile', mock_named_temp), \
             patch('mcp_nixos.utils.cache_helpers.lock_file', mock_lock_file), \
             patch('mcp_nixos.utils.cache_helpers.os.replace', mock_os_replace), \
             patch('mcp_nixos.utils.cache_helpers.ctypes.windll', mock_windll), \
             patch('mcp_nixos.utils.cache_helpers.os.path.exists', return_value=True), \
             patch('mcp_nixos.utils.cache_helpers.logger', mock_logger), \
             patch('builtins.open', m):
            
            # Call atomic_write
            result = atomic_write(r"C:\temp\target.txt", "test content")
            assert result is False
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
    
    def test_atomic_write_retry_on_failure(self):
        """Test atomic_write retry on temporary failure."""
        # Create mock temp files
        mock_temp_file1 = MagicMock()
        mock_temp_file1.name = "/tmp/tempfile1"
        mock_temp_file2 = MagicMock()
        mock_temp_file2.name = "/tmp/tempfile2"
        
        # Mock NamedTemporaryFile to return our mocks
        mock_named_temp = MagicMock(side_effect=[mock_temp_file1, mock_temp_file2])
        
        # Mock lock_file to fail once then succeed
        mock_lock_file = MagicMock(side_effect=[False, True])
        
        # Mock os.replace
        mock_os_replace = MagicMock()
        
        # Mock time.sleep
        mock_sleep = MagicMock()
        
        # Mock random.uniform to return a consistent value
        mock_uniform = MagicMock(return_value=0.1)
        
        # Mock file operations
        m = mock_open()
        
        with patch('mcp_nixos.utils.cache_helpers.tempfile.NamedTemporaryFile', mock_named_temp), \
             patch('mcp_nixos.utils.cache_helpers.lock_file', mock_lock_file), \
             patch('mcp_nixos.utils.cache_helpers.os.replace', mock_os_replace), \
             patch('mcp_nixos.utils.cache_helpers.time.sleep', mock_sleep), \
             patch('mcp_nixos.utils.cache_helpers.random.uniform', mock_uniform), \
             patch('builtins.open', m):
            
            # Call atomic_write - should succeed on the second try
            result = atomic_write("/tmp/target.txt", "test content", retries=1)
            assert result is True
            
            # Verify replace was called with the second temp file
            mock_os_replace.assert_called_once_with("/tmp/tempfile2", "/tmp/target.txt")


class TestMetadataOperations:
    """Test metadata operations in cache_helpers."""
    
    def test_write_with_metadata_default_timestamp(self):
        """Test write_with_metadata with default timestamp."""
        # Mock time.time
        mock_time = MagicMock(return_value=12345.67)
        
        # Mock atomic_write
        mock_atomic_write = MagicMock(return_value=True)
        
        # Mock json.dumps
        mock_json_dumps = MagicMock(return_value='{"data": "content", "timestamp": 12345.67}')
        
        with patch('mcp_nixos.utils.cache_helpers.time.time', mock_time), \
             patch('mcp_nixos.utils.cache_helpers.atomic_write', mock_atomic_write), \
             patch('mcp_nixos.utils.cache_helpers.json.dumps', mock_json_dumps):
            
            # Call the function with no metadata
            result = write_with_metadata("/tmp/file.json", "content")
            assert result is True
            
            # Check that time.time was called for default timestamp
            mock_time.assert_called_once()
            
            # Check that atomic_write was called with the JSON content
            mock_atomic_write.assert_called_once()
    
    def test_read_with_metadata_lock_failure(self):
        """Test read_with_metadata when lock acquisition fails."""
        # Mock open
        m = mock_open()
        
        # Mock lock_file to return False
        mock_lock_file = MagicMock(return_value=False)
        
        with patch('builtins.open', m), \
             patch('mcp_nixos.utils.cache_helpers.lock_file', mock_lock_file), \
             patch('mcp_nixos.utils.cache_helpers.os.path.exists', return_value=True):
            
            # Call the function
            data, metadata = read_with_metadata("/tmp/file.json")
            
            # Should return None for both data and metadata
            assert data is None
            assert metadata is None
            
            # Verify file was not read
            m.assert_not_called()
    
    def test_read_with_metadata_file_not_found(self):
        """Test read_with_metadata when file doesn't exist."""
        # Mock os.path.exists to return False
        with patch('mcp_nixos.utils.cache_helpers.os.path.exists', return_value=False):
            
            # Call the function
            data, metadata = read_with_metadata("/tmp/nonexistent.json")
            
            # Should return None for both data and metadata
            assert data is None
            assert metadata is None
    
    def test_read_with_metadata_json_parse_error(self):
        """Test read_with_metadata with invalid JSON."""
        # Mock open to return invalid JSON
        m = mock_open(read_data="invalid json content")
        
        # Mock lock_file to return True
        mock_lock_file = MagicMock(return_value=True)
        
        # Mock unlock_file
        mock_unlock_file = MagicMock()
        
        # Mock the logger
        mock_logger = MagicMock()
        
        with patch('builtins.open', m), \
             patch('mcp_nixos.utils.cache_helpers.lock_file', mock_lock_file), \
             patch('mcp_nixos.utils.cache_helpers.unlock_file', mock_unlock_file), \
             patch('mcp_nixos.utils.cache_helpers.logger', mock_logger), \
             patch('mcp_nixos.utils.cache_helpers.os.path.exists', return_value=True):
            
            # Call the function
            data, metadata = read_with_metadata("/tmp/file.json")
            
            # Should return None for both data and metadata
            assert data is None
            assert metadata is None
            
            # Verify error was logged
            mock_logger.error.assert_called_once()
            assert "Error parsing JSON" in mock_logger.error.call_args[0][0]