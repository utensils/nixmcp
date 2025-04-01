"""
Logging configuration for MCP-NixOS.
"""

import logging
import logging.handlers
import os
import sys
import time


def setup_logging():
    """
    Configure logging for the MCP-NixOS server.

    By default, only logs to console. If MCP_NIXOS_LOG_FILE environment variable is set,
    it will also log to the specified file path. MCP_NIXOS_LOG_LEVEL controls the logging level.

    Environment Variables:
    - MCP_NIXOS_LOG_FILE: Path to log file (if not set, logs to console only)
    - MCP_NIXOS_LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - LOG_FILE: Legacy/alias for MCP_NIXOS_LOG_FILE (for backward compatibility)
    - LOG_LEVEL: Legacy/alias for MCP_NIXOS_LOG_LEVEL (for backward compatibility)
    - LOG_FORMAT: Determines log format, can be "simple", "detailed" (default), or "json"

    Returns:
        logger: Configured logger instance
    """
    # Get standardized log configuration
    log_file = os.environ.get("MCP_NIXOS_LOG_FILE", os.environ.get("LOG_FILE"))
    log_level = os.environ.get("MCP_NIXOS_LOG_LEVEL", os.environ.get("LOG_LEVEL", "INFO")).upper()
    log_format = os.environ.get("LOG_FORMAT", "detailed").lower()

    # Create logger
    logger = logging.getLogger("mcp_nixos")

    # Set the log level
    try:
        # Directly set the level attribute to ensure the internal level value is updated
        # This addresses an issue where isEnabledFor() wasn't reflecting the level correctly
        level_value = getattr(logging, log_level)
        logger.setLevel(level_value)
        logger.level = level_value  # Explicitly set the level attribute for test compatibility
    except AttributeError:
        print(f"Invalid log level '{log_level}', using INFO")
        logger.setLevel(logging.INFO)
        logger.level = logging.INFO  # Explicitly set the level attribute for test compatibility
        log_level = "INFO"

    # Only configure handlers if they haven't been added yet
    # This prevents duplicate logging when code is reloaded
    if not logger.handlers:
        # Create formatter based on format type
        if log_format == "simple":
            formatter = logging.Formatter("%(levelname)s: %(message)s")
        elif log_format == "json":
            formatter = logging.Formatter(
                '{"timestamp":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}'
            )
        else:  # detailed is the default
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Add file handler only if log file is specified
        if log_file and log_file.strip():
            try:
                # Ensure directory exists
                log_dir = os.path.dirname(log_file)
                if log_dir:
                    os.makedirs(log_dir, exist_ok=True)

                # Create rotating file handler
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
                )
                file_handler.setLevel(getattr(logging, log_level))
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
                logger.info(f"Logging to file: {log_file}")
            except (IOError, PermissionError) as e:
                logger.error(f"Failed to set up file logging to {log_file}: {str(e)}")
                # Try a fallback location in user's home directory
                try:
                    fallback_log = os.path.expanduser("~/mcp_nixos.log")
                    fallback_handler = logging.handlers.RotatingFileHandler(
                        fallback_log, maxBytes=10 * 1024 * 1024, backupCount=3
                    )
                    fallback_handler.setLevel(getattr(logging, log_level))
                    fallback_handler.setFormatter(formatter)
                    logger.addHandler(fallback_handler)
                    logger.info(f"Using fallback log file: {fallback_log}")
                except Exception as e2:
                    logger.error(f"Failed to set up fallback logging: {str(e2)}")

        # Log initialization info
        logger.info(f"Logging initialized at level {log_level}")

        # Log diagnostic information
        pid = os.getpid()
        logger.info(f"Process ID: {pid}, Python: {sys.version.split()[0]}, Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Detect if running under Windsurf
        windsurf_env_vars = [v for v in os.environ if "WINDSURF" in v.upper() or "WINDSURFER" in v.upper()]
        if windsurf_env_vars:
            logger.info("Detected Windsurf environment")
            for var in windsurf_env_vars:
                logger.debug(f"Windsurf env: {var}={os.environ.get(var)}")

    return logger
