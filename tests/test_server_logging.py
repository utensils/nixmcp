"""Tests for the server logging configuration."""

import os
import logging
import unittest
from unittest.mock import patch, MagicMock

# Import the setup_logging function from mcp_nixos.server.py
from mcp_nixos.server import setup_logging


class TestLogging(unittest.TestCase):
    """Test cases for logging configuration."""

    def setUp(self):
        """Set up for tests by removing existing handlers."""
        # Reset logger to avoid interference between tests
        logger = logging.getLogger("mcp_nixos")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    @patch.dict(os.environ, {}, clear=True)
    def test_logging_default(self):
        """Test default logging setup with no environment variables."""
        # Patch logging.info to avoid actual output during test
        with patch.object(logging.Logger, "info"):
            logger = setup_logging()

        # Should have only one handler (console)
        self.assertEqual(len(logger.handlers), 1)
        self.assertIsInstance(logger.handlers[0], logging.StreamHandler)

    @patch.dict(os.environ, {"LOG_FILE": ""}, clear=True)
    def test_logging_empty_log_path(self):
        """Test logging setup with LOG_FILE explicitly set to empty string."""
        # Patch logging.info to avoid actual output during test
        with patch.object(logging.Logger, "info"):
            logger = setup_logging()

        # Should still have only one handler (console), as empty path should be ignored
        self.assertEqual(len(logger.handlers), 1)
        self.assertIsInstance(logger.handlers[0], logging.StreamHandler)

    @patch.dict(os.environ, {"LOG_FILE": "/tmp/test.log"}, clear=True)
    def test_logging_with_file(self):
        """Test logging setup with LOG_FILE environment variable."""
        with patch("logging.handlers.RotatingFileHandler") as mock_handler:
            # Setup a mock for the file handler with proper level attribute
            mock_instance = MagicMock()
            mock_instance.level = logging.INFO
            mock_handler.return_value = mock_instance

            # Ensure we don't actually try to log during the test
            with patch.object(logging.Logger, "info"):
                logger = setup_logging()

            # Should have two handlers (console and file)
            self.assertEqual(len(logger.handlers), 2)
            self.assertIsInstance(logger.handlers[0], logging.StreamHandler)

            # Verify the file handler was created with the correct path
            mock_handler.assert_called_once()
            args, _ = mock_handler.call_args
            self.assertEqual(args[0], "/tmp/test.log")

    @patch.dict(os.environ, {"LOG_LEVEL": "DEBUG", "LOG_FILE": "/tmp/test.log"}, clear=True)
    def test_logging_levels(self):
        """Test that log levels are set correctly."""
        with patch("logging.handlers.RotatingFileHandler") as mock_handler:
            mock_instance = MagicMock()
            mock_instance.level = logging.DEBUG
            mock_handler.return_value = mock_instance

            # Ensure we don't actually try to log during the test
            with patch.object(logging.Logger, "info"):
                logger = setup_logging()

            # Logger level should be DEBUG
            self.assertEqual(logger.level, logging.DEBUG)

            # Console handler should have DEBUG level
            self.assertEqual(logger.handlers[0].level, logging.DEBUG)

            # Verify mock file handler's level was set to DEBUG
            mock_instance.setLevel.assert_called_with(logging.DEBUG)

    @patch.dict(os.environ, {"LOG_FILE": "/nonexistent/directory/test.log"}, clear=True)
    def test_logging_file_error(self):
        """Test error handling when log file cannot be created."""
        # Simulate an error when creating the file handler
        with patch("logging.handlers.RotatingFileHandler") as mock_handler:
            mock_handler.side_effect = IOError("Failed to create log file")

            # Patch error logging to avoid actual error output
            with patch.object(logging.Logger, "error"):
                logger = setup_logging()

            # Should only have one handler (console) as file handler creation failed
            self.assertEqual(len(logger.handlers), 1)
            self.assertIsInstance(logger.handlers[0], logging.StreamHandler)


if __name__ == "__main__":
    unittest.main()
