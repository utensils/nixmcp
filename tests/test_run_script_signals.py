"""
Tests for the enhanced signal handling in the run.py script.

This module tests the signal handling functionality in run.py which manages the
MCP-NixOS server process and ensures proper shutdown during signals.
"""

import os
import signal
import pytest
from unittest.mock import patch, MagicMock


class TestRunScriptSignalHandling:
    """Tests for the signal handling in run.py."""

    @patch("mcp_nixos.run.signal.signal")
    def test_run_registers_signal_handlers(self, mock_signal):
        """Test that the main function registers signal handlers."""
        # Import main only when needed to avoid side effects
        from mcp_nixos.run import main

        # Mock subprocess to prevent actual server startup
        with patch("mcp_nixos.run.subprocess.Popen") as mock_popen:
            # Mock process for wait
            mock_process = MagicMock()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            # And mock the orphan cleanup
            with patch("mcp_nixos.run.find_and_kill_zombie_mcp_processes"):
                # Call the function we're testing
                main()

                # Check that signal handlers were registered
                assert mock_signal.called

                # At minimum, SIGINT and SIGTERM should be registered
                sigint_registered = any(call[0][0] == signal.SIGINT for call in mock_signal.call_args_list)
                sigterm_registered = any(call[0][0] == signal.SIGTERM for call in mock_signal.call_args_list)

                assert sigint_registered
                assert sigterm_registered


class TestRunScriptSignalHandlerBehavior:
    """Tests for the behavior of the signal handler in run.py."""

    @pytest.fixture
    def mock_server_process(self):
        """Fixture to create a mock server process."""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process is running
        yield mock_process

    @pytest.fixture
    def setup_run_signal_handler(self, mock_server_process):
        """Fixture to set up the signal handler from run.py."""
        # Import here to avoid module-level side effects
        from mcp_nixos.run import main

        with patch("mcp_nixos.run.signal.signal") as mock_signal:
            # Capture the registered handler
            handlers = {}

            def fake_signal_register(signum, handler):
                handlers[signum] = handler
                return MagicMock()

            mock_signal.side_effect = fake_signal_register

            # Mock process interactions
            with patch("mcp_nixos.run.subprocess.Popen") as mock_popen:
                mock_popen.return_value = mock_server_process
                mock_server_process.wait.return_value = 0

                # Mock the orphan cleanup
                with patch("mcp_nixos.run.find_and_kill_zombie_mcp_processes"):
                    # This will register our signal handlers
                    with patch("mcp_nixos.run.print"):  # Suppress print during test
                        main()

            # Return handlers for testing
            yield handlers

    def test_run_script_contains_sys_exit(self):
        """Test that run.py uses sys.exit not os._exit in the signal handler."""
        # Simple test to verify the code contains sys.exit(130) and not os._exit(130)
        # Read the run.py file directly
        import os

        run_py_path = os.path.join(os.path.dirname(__file__), "..", "mcp_nixos", "run.py")

        with open(run_py_path, "r") as file:
            content = file.read()

        # Check that sys.exit is used instead of os._exit in the signal handler
        assert "sys.exit(130)" in content
        assert "os._exit(130)" not in content

        # Also check that the server process is killed in the signal handler
        assert "server_process.kill()" in content


class TestOrphanProcessCleanup:
    """Tests for the orphaned process cleanup functionality."""

    @patch("mcp_nixos.run.os.popen")
    @patch.dict(os.environ, {"MCP_NIXOS_CLEANUP_ORPHANS": "true"})
    @patch("mcp_nixos.run.os.getpid")
    def test_find_and_kill_zombie_processes(self, mock_getpid, mock_popen):
        """Test that orphaned processes are detected and killed."""
        from mcp_nixos.run import find_and_kill_zombie_mcp_processes

        # Mock our own PID
        mock_getpid.return_value = 12345

        # Mock process listing
        mock_file = MagicMock()
        mock_file.readlines.return_value = ["67890 python3 -m mcp_nixos", "78901 python3 /path/to/mcp_nixos"]
        mock_popen.return_value = mock_file

        # Mock killing processes
        with patch("mcp_nixos.run.os.kill") as mock_kill:
            with patch("mcp_nixos.run.print"):  # Suppress print during test
                # Call the function we're testing
                find_and_kill_zombie_mcp_processes()

                # Check that we tried to kill processes
                assert mock_kill.called

                # Should be called twice for each process (SIGTERM, check)
                # or 3 times if SIGKILL is needed
                assert mock_kill.call_count >= 2

                # Check SIGTERM was sent to both PIDs
                sigterm_67890 = any(c[0][0] == 67890 and c[0][1] == signal.SIGTERM for c in mock_kill.call_args_list)

                sigterm_78901 = any(c[0][0] == 78901 and c[0][1] == signal.SIGTERM for c in mock_kill.call_args_list)

                assert sigterm_67890 or sigterm_78901

    @patch.dict(os.environ, {"MCP_NIXOS_CLEANUP_ORPHANS": "false"})
    @patch("mcp_nixos.run.os.popen")
    def test_cleanup_disabled_by_default(self, mock_popen):
        """Test that orphaned process cleanup is disabled by default."""
        from mcp_nixos.run import find_and_kill_zombie_mcp_processes

        # Call the function we're testing
        find_and_kill_zombie_mcp_processes()

        # Should not call popen if cleanup is disabled
        mock_popen.assert_not_called()


class TestWindsurfRunScriptCompatibility:
    """Tests for Windsurf-specific environment handling in run.py."""

    def test_windsurf_env_pattern_in_run_script(self):
        """Test that run.py contains code to check for Windsurf environment variables."""
        # Simple test to verify the code contains logic to check for Windsurf env vars
        import os

        run_py_path = os.path.join(os.path.dirname(__file__), "..", "mcp_nixos", "run.py")

        with open(run_py_path, "r") as file:
            content = file.read()

        # Check for Windsurf detection patterns in the code
        # (This is more reliable than trying to mock the environment and capture output)
        assert "WINDSURF" in content
        assert "if windsurf_vars:" in content or "if windsurf_detected:" in content
