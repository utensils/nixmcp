"""Tests for orphaned process cleanup functionality in run.py."""

import os
import unittest
import pytest
from unittest.mock import patch, MagicMock

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

from mcp_nixos.run import find_and_kill_zombie_mcp_processes


@pytest.mark.unit
class TestOrphanProcessCleanup(unittest.TestCase):
    """Test suite for orphaned process cleanup functionality."""

    @patch("os.popen")
    @patch("os.kill")
    @patch("time.sleep")
    def test_cleanup_disabled_by_default(self, mock_sleep, mock_kill, mock_popen):
        """Test that orphaned process cleanup is disabled by default."""
        # Setup mock to simulate process discovery
        mock_process = MagicMock()
        mock_process.readlines.return_value = ["12345 python -m mcp_nixos"]
        mock_process.close.return_value = None
        mock_popen.return_value = mock_process

        # Clear any existing env var to ensure default behavior
        if "MCP_NIXOS_CLEANUP_ORPHANS" in os.environ:
            del os.environ["MCP_NIXOS_CLEANUP_ORPHANS"]

        # Run the function
        find_and_kill_zombie_mcp_processes()

        # Verify it doesn't attempt to kill any processes
        mock_popen.assert_not_called()
        mock_kill.assert_not_called()

    @patch("psutil.process_iter")
    @patch("time.sleep")
    def test_cleanup_when_enabled(self, mock_sleep, mock_process_iter):
        """Test that orphaned processes are cleaned up when enabled."""
        # Setup mock psutil process
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.name.return_value = "python"
        mock_proc.cmdline.return_value = ["python", "-m", "mcp_nixos"]

        # Setup process_iter to return our mock process
        mock_process_iter.return_value = [mock_proc]

        # Enable cleanup
        os.environ["MCP_NIXOS_CLEANUP_ORPHANS"] = "true"

        # Get current pid before patching
        with patch("os.getpid", return_value=9999):  # Different from our mock process
            # Run the function
            find_and_kill_zombie_mcp_processes()

            # Verify it terminates the process
            mock_proc.terminate.assert_called_once()
            # Should try to wait for the process to end
            mock_proc.wait.assert_called_once()

    @patch("psutil.process_iter")
    @patch("time.sleep")
    def test_sigkill_for_stubborn_processes(self, mock_sleep, mock_process_iter):
        """Test that SIGKILL is used for processes that don't terminate with SIGTERM."""
        # Setup mock psutil process that won't terminate with SIGTERM
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.name.return_value = "python"
        mock_proc.cmdline.return_value = ["python", "-m", "mcp_nixos"]

        # Make wait time out to simulate a process that doesn't respond to SIGTERM
        # Using proper TimeoutExpired constructor with required parameters for cross-platform compatibility
        import psutil

        # TimeoutExpired expects process ID as first parameter, not a named 'proc' parameter
        mock_proc.wait.side_effect = psutil.TimeoutExpired(mock_proc.pid, 0.5)

        # Setup process_iter to return our mock process
        mock_process_iter.return_value = [mock_proc]

        # Enable cleanup
        os.environ["MCP_NIXOS_CLEANUP_ORPHANS"] = "true"

        # Run with a mock for getpid
        with patch("os.getpid", return_value=9999):  # Different from our mock process
            # Run the function
            find_and_kill_zombie_mcp_processes()

            # Verify it terminates the process with both signals
            mock_proc.terminate.assert_called_once()
            mock_proc.wait.assert_called_once()
            mock_proc.kill.assert_called_once()  # Should use kill after terminate fails

    def test_different_env_values(self):
        """Test different environment variable values."""
        test_cases = [
            # (env_value, should_cleanup)
            ("true", True),
            ("TRUE", True),
            ("True", True),
            ("false", False),
            ("FALSE", False),
            ("False", False),
            ("0", False),
            ("1", False),
            ("yes", False),
            ("no", False),
            ("", False),
        ]

        for env_value, should_cleanup in test_cases:
            with self.subTest(f"Testing env value: {env_value}"):
                # Set env var
                os.environ["MCP_NIXOS_CLEANUP_ORPHANS"] = env_value

                # Mock psutil.process_iter for process discovery
                with patch("psutil.process_iter") as mock_process_iter:
                    # Setup mock process
                    mock_proc = MagicMock()
                    mock_proc.pid = 12345
                    mock_proc.name.return_value = "python"
                    mock_proc.cmdline.return_value = ["python", "-m", "mcp_nixos"]
                    mock_process_iter.return_value = [mock_proc]

                    # Mock getpid to avoid interference
                    with patch("os.getpid", return_value=9999):
                        # Run the function
                        find_and_kill_zombie_mcp_processes()

                        # Verify behavior based on whether cleanup should happen
                        if should_cleanup:
                            # Verify process discovery is called
                            mock_process_iter.assert_called_once()
                            # Verify process filtering by checking terminate was called
                            # on processes that match our criteria
                            mock_proc.terminate.assert_called_once()
                        else:
                            # Verify process discovery is not called when cleanup is disabled
                            mock_process_iter.assert_not_called()
                            # Verify no termination happens
                            self.assertFalse(
                                hasattr(mock_proc, "terminate") and mock_proc.terminate.called,
                                f"Process should not be terminated when env value is {env_value}",
                            )


if __name__ == "__main__":
    unittest.main()
