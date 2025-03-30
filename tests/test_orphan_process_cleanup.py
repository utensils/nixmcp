"""Tests for orphaned process cleanup functionality in run.py."""

import os
import signal
import unittest
from unittest.mock import patch, MagicMock

from mcp_nixos.run import find_and_kill_zombie_mcp_processes


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

    @patch("os.popen")
    @patch("os.kill")
    @patch("time.sleep")
    def test_cleanup_when_enabled(self, mock_sleep, mock_kill, mock_popen):
        """Test that orphaned processes are cleaned up when enabled."""
        # Setup mock to simulate process discovery
        mock_process = MagicMock()
        mock_process.readlines.return_value = ["12345 python -m mcp_nixos"]
        mock_process.close.return_value = None
        mock_popen.return_value = mock_process

        # First kill returns nothing (success)
        # Second kill (check) raises OSError to simulate successful termination
        mock_kill.side_effect = [None, OSError()]

        # Enable cleanup
        os.environ["MCP_NIXOS_CLEANUP_ORPHANS"] = "true"

        # Run the function
        find_and_kill_zombie_mcp_processes()

        # Verify it attempts to kill the process
        mock_popen.assert_called_once()
        # Should call kill twice: once for SIGTERM, once for checking with signal 0
        self.assertEqual(mock_kill.call_count, 2)
        # Verify the first call was with SIGTERM
        mock_kill.assert_any_call(12345, signal.SIGTERM)

    @patch("os.popen")
    @patch("os.kill")
    @patch("time.sleep")
    def test_sigkill_for_stubborn_processes(self, mock_sleep, mock_kill, mock_popen):
        """Test that SIGKILL is used for processes that don't terminate with SIGTERM."""
        # Setup mock to simulate process discovery
        mock_process = MagicMock()
        mock_process.readlines.return_value = ["12345 python -m mcp_nixos"]
        mock_process.close.return_value = None
        mock_popen.return_value = mock_process

        # First kill returns nothing (success for SIGTERM)
        # Second kill (check) returns nothing (process still exists)
        # Third kill returns nothing (success for SIGKILL)
        mock_kill.side_effect = [None, None, None]

        # Enable cleanup
        os.environ["MCP_NIXOS_CLEANUP_ORPHANS"] = "true"

        # Run the function
        find_and_kill_zombie_mcp_processes()

        # Verify it attempts to kill the process with both signals
        mock_popen.assert_called_once()
        # Should call kill three times: SIGTERM, check, SIGKILL
        self.assertEqual(mock_kill.call_count, 3)
        # Verify SIGTERM was used first
        mock_kill.assert_any_call(12345, signal.SIGTERM)
        # Verify SIGKILL was used as fallback
        mock_kill.assert_any_call(12345, signal.SIGKILL)

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
                with patch("os.popen") as mock_popen:
                    # Setup mock
                    mock_process = MagicMock()
                    mock_process.readlines.return_value = ["12345 python -m mcp_nixos"]
                    mock_process.close.return_value = None
                    if should_cleanup:
                        mock_popen.return_value = mock_process

                    # Set env var
                    os.environ["MCP_NIXOS_CLEANUP_ORPHANS"] = env_value

                    # Mock kill to avoid actually killing anything
                    with patch("os.kill"):
                        # Run the function
                        find_and_kill_zombie_mcp_processes()

                        # Verify behavior
                        if should_cleanup:
                            mock_popen.assert_called_once()
                        else:
                            mock_popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
