"""Tests for the main module entry point of MCP-NixOS."""

from unittest.mock import patch
import os
import pytest

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit

# Import the __main__ module
from mcp_nixos.__main__ import parse_args, main


class TestMainModule:
    """Tests for the __main__ module functions of MCP-NixOS."""

    def test_parse_args_default(self):
        """Test parsing command line arguments with default values."""
        with patch("sys.argv", ["mcp_nixos"]):
            args = parse_args()
            assert not args.pre_cache

    def test_parse_args_pre_cache(self):
        """Test parsing command line arguments with pre-cache flag."""
        with patch("sys.argv", ["mcp_nixos", "--pre-cache"]):
            args = parse_args()
            assert args.pre_cache

    @patch("mcp_nixos.__main__.run_precache")
    def test_main_pre_cache_mode(self, mock_run_precache):
        """Test running in pre-cache mode."""
        with patch("sys.argv", ["mcp_nixos", "--pre-cache"]):
            # Mock logger to avoid actual logging
            with patch("mcp_nixos.__main__.logger") as mock_logger:
                result = main()

                # Verify pre-cache was run
                mock_run_precache.assert_called_once()

                # Verify logging calls
                mock_logger.info.assert_any_call("Running in pre-cache mode - will exit after caching completes")
                mock_logger.info.assert_any_call("Pre-cache completed successfully")

                # Verify return code
                assert result == 0

    @patch("mcp_nixos.__main__.mcp")
    def test_main_server_mode(self, mock_mcp):
        """Test running in server mode."""
        with patch("sys.argv", ["mcp_nixos"]):
            # Mock logger to avoid actual logging
            with patch("mcp_nixos.__main__.logger") as mock_logger:
                main()

                # Verify server was run
                mock_mcp.run.assert_called_once()

                # Verify logging calls
                mock_logger.info.assert_any_call("Starting server main loop")

    @patch("mcp_nixos.__main__.mcp")
    def test_main_keyboard_interrupt(self, mock_mcp):
        """Test handling of keyboard interrupt."""
        with patch("sys.argv", ["mcp_nixos"]):
            # Make mcp.run raise KeyboardInterrupt
            mock_mcp.run.side_effect = KeyboardInterrupt()

            # Mock logger and sys.exit to avoid actual logging and exit
            with patch("mcp_nixos.__main__.logger") as mock_logger:
                with patch("mcp_nixos.__main__.sys.exit") as mock_exit:
                    main()

                    # Verify log message
                    mock_logger.info.assert_any_call("Server stopped by keyboard interrupt")

                    # Verify exit was called with code 0
                    mock_exit.assert_called_once_with(0)

    @patch("mcp_nixos.__main__.mcp")
    def test_main_exception(self, mock_mcp):
        """Test handling of unexpected exceptions."""
        with patch("sys.argv", ["mcp_nixos"]):
            # Make mcp.run raise an exception
            mock_mcp.run.side_effect = Exception("Test error")

            # Mock logger and sys.exit to avoid actual logging and exit
            with patch("mcp_nixos.__main__.logger") as mock_logger:
                with patch("mcp_nixos.__main__.sys.exit") as mock_exit:
                    main()

                    # Verify log message
                    mock_logger.error.assert_called_once()
                    assert "Test error" in mock_logger.error.call_args[0][0]

                    # Verify exit was called with code 1
                    mock_exit.assert_called_once_with(1)

    def test_windsurf_detection(self):
        """Test detection of Windsurf environment variables."""
        with patch("sys.argv", ["mcp_nixos"]):
            # Set up environment with Windsurf variables
            with patch.dict(os.environ, {"WINDSURF_VERSION": "1.0", "WINDSURFER_ID": "test"}):
                # Mock logger, mcp, and sys.exit to avoid actual logging and exit
                with patch("mcp_nixos.__main__.logger") as mock_logger:
                    with patch("mcp_nixos.__main__.mcp"):
                        main()

                        # Verify log messages about Windsurf environment
                        mock_logger.info.assert_any_call("Detected Windsurf environment variable: WINDSURF_VERSION=1.0")
                        mock_logger.info.assert_any_call("Detected Windsurf environment variable: WINDSURFER_ID=test")
                        mock_logger.info.assert_any_call(
                            "Running under Windsurf - monitoring for restart/refresh signals"
                        )
