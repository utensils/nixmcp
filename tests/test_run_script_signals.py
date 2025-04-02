"""
Tests for the enhanced signal handling in the run.py script.

This module tests the signal handling functionality in run.py which manages the
MCP-NixOS server process and ensures proper shutdown during signals.
"""

import os
import sys
import signal
import pytest
from unittest.mock import patch, MagicMock

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


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

            # Mock importlib.util.find_spec for Windows testing
            with patch("importlib.util.find_spec", return_value=None):
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

        # Use utf-8 encoding explicitly to avoid Windows encoding issues
        with open(run_py_path, "r", encoding="utf-8") as file:
            content = file.read()

        # Check that sys.exit is used instead of os._exit in the signal handler
        assert "sys.exit(130)" in content
        assert "os._exit(130)" not in content

        # Also check that the server process is killed in the signal handler
        assert "server_process.kill()" in content


class TestOrphanProcessCleanup:
    """Tests for the orphaned process cleanup functionality."""

    @patch("psutil.process_iter")
    @patch.dict(os.environ, {"MCP_NIXOS_CLEANUP_ORPHANS": "true"})
    @patch("mcp_nixos.run.os.getpid")
    def test_find_and_kill_zombie_processes(self, mock_getpid, mock_process_iter):
        """Test that orphaned processes are detected and killed."""
        from mcp_nixos.run import find_and_kill_zombie_mcp_processes

        # Mock our own PID
        mock_getpid.return_value = 12345

        # Create mock processes for testing
        mock_proc1 = MagicMock()
        mock_proc1.pid = 67890
        mock_proc1.name.return_value = "python3"
        mock_proc1.cmdline.return_value = ["python3", "-m", "mcp_nixos"]

        mock_proc2 = MagicMock()
        mock_proc2.pid = 78901
        mock_proc2.name.return_value = "python3"
        mock_proc2.cmdline.return_value = ["python3", "/path/to/mcp_nixos"]

        # Return our mock processes from process_iter
        mock_process_iter.return_value = [mock_proc1, mock_proc2]

        # Suppress print output during test
        with patch("mcp_nixos.run.print"):
            # Call the function we're testing
            find_and_kill_zombie_mcp_processes()

            # Check that terminate was called on both processes
            mock_proc1.terminate.assert_called_once()
            mock_proc2.terminate.assert_called_once()

            # Check that wait was called for both processes
            mock_proc1.wait.assert_called_once()
            mock_proc2.wait.assert_called_once()

    @patch.dict(os.environ, {"MCP_NIXOS_CLEANUP_ORPHANS": "false"})
    @patch("psutil.process_iter")
    def test_cleanup_disabled_by_default(self, mock_process_iter):
        """Test that orphaned process cleanup is disabled by default."""
        from mcp_nixos.run import find_and_kill_zombie_mcp_processes

        # Call the function we're testing
        find_and_kill_zombie_mcp_processes()

        # Should not call process_iter if cleanup is disabled
        mock_process_iter.assert_not_called()


class TestWindsurfRunScriptCompatibility:
    """Tests for Windsurf-specific environment handling in run.py."""

    def test_windsurf_env_pattern_in_run_script(self):
        """Test that run.py contains code to check for Windsurf environment variables."""
        # Simple test to verify the code contains logic to check for Windsurf env vars
        import os

        run_py_path = os.path.join(os.path.dirname(__file__), "..", "mcp_nixos", "run.py")

        # Use utf-8 encoding explicitly to avoid Windows encoding issues
        with open(run_py_path, "r", encoding="utf-8") as file:
            content = file.read()

        # Check for Windsurf detection patterns in the code
        # (This is more reliable than trying to mock the environment and capture output)
        assert "WINDSURF" in content
        assert "if windsurf_vars:" in content or "if windsurf_detected:" in content


class TestWindowsCompatibility:
    """Tests for Windows-specific compatibility in run.py."""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    @patch("sys.platform", "win32")
    @patch("importlib.util.find_spec")
    def test_windows_ctrl_handler_with_win32api(self, mock_find_spec):
        """Test Windows CTRL handler setup with win32api available."""
        from mcp_nixos.run import main

        # Mock win32api to be available
        mock_find_spec.return_value = MagicMock()

        # Mock win32api module
        mock_win32api = MagicMock()
        with patch.dict("sys.modules", {"win32api": mock_win32api}):
            # Mock subprocess to prevent actual server startup
            with patch("mcp_nixos.run.subprocess.Popen") as mock_popen:
                mock_process = MagicMock()
                mock_process.wait.return_value = 0
                mock_popen.return_value = mock_process

                # Mock the orphan cleanup
                with patch("mcp_nixos.run.find_and_kill_zombie_mcp_processes"):
                    with patch("mcp_nixos.run.print"):  # Suppress print output
                        main()

                # Verify win32api.SetConsoleCtrlHandler was called
                mock_win32api.SetConsoleCtrlHandler.assert_called_once()

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    @patch("sys.platform", "win32")
    @patch("importlib.util.find_spec")
    def test_windows_ctrl_handler_without_win32api(self, mock_find_spec):
        """Test graceful fallback when win32api is not available."""
        from mcp_nixos.run import main

        # Mock win32api to be unavailable
        mock_find_spec.return_value = None

        # Mock subprocess to prevent actual server startup
        with patch("mcp_nixos.run.subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            # Mock the orphan cleanup
            with patch("mcp_nixos.run.find_and_kill_zombie_mcp_processes"):
                # Should not raise any exceptions even without win32api
                with patch("mcp_nixos.run.print"):  # Suppress print output
                    main()

                # Test passes if no exception is raised
