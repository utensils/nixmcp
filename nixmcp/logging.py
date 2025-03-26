"""
Logging configuration for NixMCP.
"""

import os
import logging
import logging.handlers


def setup_logging():
    """
    Configure logging for the NixMCP server.

    By default, only logs to console. If NIX_MCP_LOG environment variable is set,
    it will also log to the specified file path. LOG_LEVEL controls the logging level.

    Returns:
        logger: Configured logger instance
    """
    log_file = os.environ.get("NIX_MCP_LOG")
    log_level = os.environ.get("LOG_LEVEL", "INFO")

    # Create logger
    logger = logging.getLogger("nixmcp")

    # Only configure handlers if they haven't been added yet
    # This prevents duplicate logging when code is reloaded
    if not logger.handlers:
        logger.setLevel(getattr(logging, log_level))

        # Create formatter
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Add file handler only if NIX_MCP_LOG is set and not empty
        if log_file and log_file.strip():
            try:
                file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
                file_handler.setLevel(getattr(logging, log_level))
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
                logger.info(f"Logging to file: {log_file}")
            except (IOError, PermissionError) as e:
                logger.error(f"Failed to set up file logging to {log_file}: {str(e)}")

        logger.info("Logging initialized")

    return logger
