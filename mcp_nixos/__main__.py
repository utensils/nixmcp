#!/usr/bin/env python
"""
CLI entry point for MCP-NixOS server.

This handles the top-level execution of the MCP-NixOS server, including proper
signal handling and graceful shutdown on keyboard interrupts.
"""

import sys
import signal

# Import mcp from server
from mcp_nixos.server import mcp, logger

# Flag to track if shutdown is already in progress
shutdown_in_progress = False


def signal_handler(signum, frame):
    """Handle termination signals with proper logging and process exit."""
    global shutdown_in_progress

    if shutdown_in_progress:
        # If we get a second signal during shutdown, exit immediately
        logger.warning("Received second signal during shutdown, exiting immediately")
        sys.exit(130)  # 128 + SIGINT value (2)

    # Mark shutdown as in progress
    shutdown_in_progress = True

    # Log the signal event
    try:
        sig_name = signal.Signals(signum).name
        logger.info(f"Received {sig_name}, initiating graceful shutdown")
    except (ValueError, AttributeError):
        logger.info(f"Received signal {signum}, initiating graceful shutdown")

    # Exit the process with appropriate code
    # This will trigger proper cleanup in the MCP framework
    sys.exit(130)  # 128 + SIGINT value (2)


def main():
    """Run the MCP-NixOS server with proper signal handling."""
    # Register signal handlers for graceful termination
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal_handler)

    try:
        # Run the server (this is a blocking call)
        mcp.run()
    except KeyboardInterrupt:
        # Handle keyboard interrupt for cleaner exit
        logger.info("Server stopped by keyboard interrupt")
        sys.exit(0)
    except Exception as e:
        # Log unexpected errors and exit with error code
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


# Expose mcp for entry point script
# This is needed for the "mcp-nixos = "mcp_nixos.__main__:mcp.run" entry point in pyproject.toml

if __name__ == "__main__":
    main()
