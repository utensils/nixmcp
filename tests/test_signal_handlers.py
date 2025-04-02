"""
Tests for signal handling in MCP-NixOS.

This module tests the signal handling functionality implemented in run.py.
It validates that the correct signal handlers are registered in run.py and that they behave as expected.
"""

import os
import signal
import logging
import pytest
from unittest.mock import patch, MagicMock

# Mark as unit tests
pytestmark = pytest.mark.unit


class TestSignalHandling:
    """Tests for the signal handling functionality in run.py."""

    @patch("mcp_nixos.run.signal.signal")
    def test_signal_handlers_registered(self, mock_signal):
        """Test that signal handlers are registered for expected signals."""
        # Import here to avoid module level side effects
        from mcp_nixos.run import main

        # Mock subprocess to prevent actual server startup
        with patch("mcp_nixos.run.subprocess.Popen") as mock_popen:
            # Mock process for wait
            mock_process = MagicMock()
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            # And mock the orphan cleanup
            with patch("mcp_nixos.run.find_and_kill_zombie_mcp_processes"):
                # Add print mock to avoid output
                with patch("builtins.print"):
                    # Call the function we're testing
                    main()

        # Check that signal.signal was called for SIGINT and SIGTERM
        registered_signals = [c[0][0] for c in mock_signal.call_args_list]

        # Verify SIGINT and SIGTERM were registered
        assert signal.SIGINT in registered_signals
        assert signal.SIGTERM in registered_signals


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
                # Mock print to avoid output
                with patch("builtins.print"):
                    # Call the function we're testing
                    main()

        # Check that signal.signal was called for SIGINT and SIGTERM
        registered_signals = [c[0][0] for c in mock_signal.call_args_list]

        # Verify SIGINT and SIGTERM were registered
        assert signal.SIGINT in registered_signals
        assert signal.SIGTERM in registered_signals

    def test_run_script_contains_sys_exit(self):
        """Test that run.py uses sys.exit not os._exit in the signal handler."""
        # Simple test to verify the code contains sys.exit(130) and not os._exit(130)
        # Read the run.py file directly
        import os

        run_py_path = os.path.join(os.path.dirname(__file__), "..", "mcp_nixos", "run.py")

        with open(run_py_path, "r", encoding="utf-8") as file:
            content = file.read()

        # Check that sys.exit is used instead of os._exit
        assert "sys.exit(130)" in content
        assert "os._exit(130)" not in content


# The TestMainScriptSignalHandling class is no longer needed since __main__.py
# no longer handles signals directly. The signals are managed by FastMCP and run.py.


class TestWindsurfCompatibility:
    """Tests for Windsurf-specific environment detection and handling."""

    @patch.dict(os.environ, {"WINDSURF_SOMETHING": "true"})
    def test_windsurf_environment_detection(self):
        """Test that Windsurf environment variables are detected and logged in logging module."""
        # Reset any existing logger configuration
        logger = logging.getLogger("mcp_nixos")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Import at test time for clean logger state
        from mcp_nixos.logging import setup_logging

        with patch("logging.Logger.info") as mock_info:
            with patch("logging.Logger.debug") as mock_debug:
                # Setup logging
                setup_logging()

                # Check that Windsurf environment was detected
                windsurf_detected = any("Detected Windsurf environment" in str(c) for c in mock_info.call_args_list)
                assert windsurf_detected

                # Check that Windsurf env vars were logged
                windsurf_vars_logged = any("WINDSURF" in str(c) for c in mock_debug.call_args_list)
                assert windsurf_vars_logged

    @patch.dict(os.environ, {"MCP_NIXOS_LOG_FILE": "/tmp/mcp_nixos_test.log"})
    def test_logging_configuration(self):
        """Test that logging is configured correctly with MCP_NIXOS_LOG_FILE."""
        # Reset any existing logger configuration
        logger = logging.getLogger("mcp_nixos")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Import at test time for clean logger state
        from mcp_nixos.logging import setup_logging

        # Create a handler mock that works with logging
        handler_mock = MagicMock()
        handler_mock.level = logging.INFO

        with patch("logging.handlers.RotatingFileHandler", return_value=handler_mock) as mock_handler:
            # Mock logger.info to avoid errors with MagicMock handler
            with patch("logging.Logger.info"):
                # Setup logging
                setup_logging()

                # Check that log file handler was created with correct path
                mock_handler.assert_called()
                assert "/tmp/mcp_nixos_test.log" in str(mock_handler.call_args)
