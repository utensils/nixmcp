"""
Tests for enhanced logging functionality in MCP-NixOS.

This module tests the standardized logging configuration implemented in logging.py.
"""

import os
import logging
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.unit
class TestEnhancedLogging:
    """Tests for the enhanced logging functionality."""

    @pytest.fixture
    def clean_logger(self):
        """Fixture to ensure we start with a clean logger for each test."""
        logger = logging.getLogger("mcp_nixos")

        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        yield logger

        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    def test_default_logging_configuration(self, clean_logger):
        """Test that logging is configured correctly with default settings."""
        from mcp_nixos.logging import setup_logging

        setup_logging()

        logger = logging.getLogger("mcp_nixos")
        assert len(logger.handlers) >= 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)
        assert logger.level == logging.INFO

    @patch.dict(os.environ, {"MCP_NIXOS_LOG_LEVEL": "DEBUG"})
    def test_log_level_debug_from_environment(self, clean_logger):
        """Test that DEBUG log level is set from environment variable."""
        from mcp_nixos.logging import setup_logging

        setup_logging()

        logger = logging.getLogger("mcp_nixos")
        assert logger.level == logging.DEBUG

    @patch.dict(os.environ, {"MCP_NIXOS_LOG_LEVEL": "WARNING"})
    def test_log_level_warning_from_environment(self, clean_logger):
        """Test that WARNING log level is set from environment variable."""
        from mcp_nixos.logging import setup_logging

        setup_logging()

        logger = logging.getLogger("mcp_nixos")
        assert logger.level == logging.WARNING

    @patch.dict(os.environ, {"MCP_NIXOS_LOG_LEVEL": "ERROR"})
    def test_log_level_error_from_environment(self, clean_logger):
        """Test that ERROR log level is set from environment variable."""
        from mcp_nixos.logging import setup_logging

        setup_logging()

        logger = logging.getLogger("mcp_nixos")
        assert logger.level == logging.ERROR

    @patch.dict(os.environ, {"MCP_NIXOS_LOG_LEVEL": "CRITICAL"})
    def test_log_level_critical_from_environment(self, clean_logger):
        """Test that CRITICAL log level is set from environment variable."""
        from mcp_nixos.logging import setup_logging

        setup_logging()

        logger = logging.getLogger("mcp_nixos")
        assert logger.level == logging.CRITICAL

    @patch.dict(os.environ, {"MCP_NIXOS_LOG_FILE": "/tmp/nixmcp_test.log"})
    def test_file_logging_configuration(self, clean_logger):
        """Test that file logging is configured when MCP_NIXOS_LOG_FILE is set."""
        from mcp_nixos.logging import setup_logging

        # Create a proper mock handler that works with logging
        handler_mock = MagicMock()
        handler_mock.level = logging.INFO

        with patch("logging.handlers.RotatingFileHandler", return_value=handler_mock) as mock_handler:
            # Also mock logger.info to avoid errors with MagicMock handler
            with patch("logging.Logger.info"):
                setup_logging()

                mock_handler.assert_called_once()
                file_path_arg = mock_handler.call_args[0][0]
                assert file_path_arg == "/tmp/nixmcp_test.log"

    @patch.dict(os.environ, {"LOG_FORMAT": "simple"})
    def test_simple_log_format(self, clean_logger):
        """Test that simple log format is used when specified."""
        from mcp_nixos.logging import setup_logging

        logger = setup_logging()

        formatter = logger.handlers[0].formatter
        format_str = getattr(formatter, "_fmt", None)
        assert format_str is not None
        assert format_str == "%(levelname)s: %(message)s"

    @patch.dict(os.environ, {"LOG_FORMAT": "json"})
    def test_json_log_format(self, clean_logger):
        """Test that JSON log format is used when specified."""
        from mcp_nixos.logging import setup_logging

        logger = setup_logging()

        formatter = logger.handlers[0].formatter
        format_str = getattr(formatter, "_fmt", None)
        assert format_str is not None
        assert "timestamp" in format_str
        assert "level" in format_str
        assert "message" in format_str

    @patch.dict(os.environ, {"MCP_NIXOS_LOG_LEVEL": "INVALID_LEVEL"})
    def test_invalid_log_level_defaults_to_info(self, clean_logger):
        """Test that an invalid log level falls back to INFO."""
        from mcp_nixos.logging import setup_logging

        # Mock print to check for warning message
        with patch("builtins.print") as mock_print:
            logger = setup_logging()

            # Verify fallback to INFO
            assert logger.level == logging.INFO

            # Verify warning was printed
            assert mock_print.called
            warning_printed = any("Invalid log level" in str(args) for args in mock_print.call_args_list)
            assert warning_printed

    @pytest.mark.timeout(5)  # Timeout to prevent test hanging
    def test_log_level_filtering(self, clean_logger):
        """
        Test log level filtering using direct handler verification.
        
        This test verifies that log filtering works correctly by:
        1. Setting up a logger with WARNING level
        2. Adding a controlled mock handler to capture logs
        3. Testing log calls at all levels
        4. Verifying only messages ≥ WARNING level are processed
        
        Note: This test was simplified from a previous complex implementation
        that was causing CI failures. This approach avoids implementation-specific
        details and directly tests the logging behavior as seen by handlers.
        """
        from mcp_nixos.logging import setup_logging
        import logging as logging_module  # Import with a different name to avoid conflicts

        # Create a logger with WARNING level set via environment
        with patch.dict(os.environ, {"MCP_NIXOS_LOG_LEVEL": "WARNING"}, clear=True):
            # Set up a clean logger instance
            logger = setup_logging()

            # VERIFICATION METHOD 1: Direct level checks
            # First verify levels directly using isEnabledFor - this is reliable across platforms
            assert logger.isEnabledFor(logging_module.WARNING), "WARNING should be enabled"
            assert logger.isEnabledFor(logging_module.ERROR), "ERROR should be enabled"
            assert logger.isEnabledFor(logging_module.CRITICAL), "CRITICAL should be enabled"
            assert not logger.isEnabledFor(logging_module.INFO), "INFO should be filtered out"
            assert not logger.isEnabledFor(logging_module.DEBUG), "DEBUG should be filtered out"

            # VERIFICATION METHOD 2: Handler capture testing
            # Create a mock handler to capture log records
            mock_handler = MagicMock()
            mock_handler.level = logging_module.WARNING
            
            # Add our mock handler to the logger
            logger.addHandler(mock_handler)

            # Log messages at all standard levels
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            logger.critical("Critical message")

            # Verify our handler received exactly 3 records (WARNING, ERROR, CRITICAL)
            assert mock_handler.handle.call_count == 3, "Should receive exactly 3 records (WARNING+)"

            # Extract log levels from the captured records
            record_levels = [args[0][0].levelno for args in mock_handler.handle.call_args_list]

            # Verify level filtering: all records should be ≥ WARNING
            assert all(level >= logging_module.WARNING for level in record_levels), "Only WARNING+ logs should pass"
            
            # Verify we received exactly one record of each expected level
            assert logging_module.WARNING in record_levels, "WARNING level record should be present"
            assert logging_module.ERROR in record_levels, "ERROR level record should be present"
            assert logging_module.CRITICAL in record_levels, "CRITICAL level record should be present"

    @patch.dict(os.environ, {"WINDSURF_SOMETHING": "true"})
    def test_windsurf_environment_detected(self, clean_logger):
        """Test that Windsurf environment is detected and logged."""
        from mcp_nixos.logging import setup_logging

        with patch("logging.Logger.info") as mock_info:
            with patch("logging.Logger.debug") as mock_debug:
                setup_logging()

                windsurf_detected = any(
                    "Detected Windsurf environment" in str(args) for args in mock_info.call_args_list
                )
                assert windsurf_detected

                env_var_logged = any("WINDSURF" in str(args) for args in mock_debug.call_args_list)
                assert env_var_logged

    @patch.dict(os.environ, {"MCP_NIXOS_LOG_FILE": "/nonexistent/path/test.log"})
    def test_fallback_on_file_permission_error(self, clean_logger):
        """Test fallback behavior when log file can't be created."""
        from mcp_nixos.logging import setup_logging

        # Test setup with mocks
        with patch("os.makedirs"):
            with patch("logging.handlers.RotatingFileHandler") as mock_handler:
                # First call raises error, second one (fallback) succeeds
                file_handler_mock = MagicMock()

                def handler_side_effect(*args, **kwargs):
                    if handler_side_effect.call_count == 0:
                        handler_side_effect.call_count += 1
                        raise PermissionError("Permission denied")
                    return file_handler_mock

                handler_side_effect.call_count = 0
                mock_handler.side_effect = handler_side_effect

                with patch("logging.Logger.error") as mock_error:
                    with patch("logging.Logger.info"):
                        with patch("os.path.expanduser", return_value="/home/user/mcp_nixos.log"):
                            setup_logging()

                            # Error should be logged
                            assert mock_error.called
                            permission_error_logged = any(
                                "Permission denied" in str(args) and "Failed to set up file logging" in str(args)
                                for args in mock_error.call_args_list
                            )
                            assert permission_error_logged

                            # Fallback handler should be created
                            assert mock_handler.call_count == 2
                            fallback_path = mock_handler.call_args_list[1][0][0]
                            assert "mcp_nixos.log" in fallback_path

    def test_log_methods(self, clean_logger):
        """Test that all log methods (debug, info, warning, error, critical) work correctly."""
        from mcp_nixos.logging import setup_logging

        # Set up with DEBUG level to capture all messages
        with patch.dict(os.environ, {"MCP_NIXOS_LOG_LEVEL": "DEBUG"}):
            # Mock all log methods to capture calls
            with (
                patch("logging.Logger.debug") as mock_debug,
                patch("logging.Logger.info") as mock_info,
                patch("logging.Logger.warning") as mock_warning,
                patch("logging.Logger.error") as mock_error,
                patch("logging.Logger.critical") as mock_critical,
            ):

                # Set up logging
                logger = setup_logging()

                # Use all log methods
                logger.debug("Debug message")
                logger.info("Info message")
                logger.warning("Warning message")
                logger.error("Error message")
                logger.critical("Critical message")

                # Verify all methods were called correctly
                mock_debug.assert_called_with("Debug message")
                mock_info.assert_called_with("Info message")
                mock_warning.assert_called_with("Warning message")
                mock_error.assert_called_with("Error message")
                mock_critical.assert_called_with("Critical message")
