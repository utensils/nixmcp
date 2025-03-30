#!/usr/bin/env python
"""
Run script for MCP-NixOS server with enhanced signal handling and clean termination.

This script wraps the MCP-NixOS server with improved signal handling to ensure
that the process cleanly terminates upon receiving SIGINT or SIGTERM signals.
It addresses the specific issue of the server appearing to hang after Ctrl+C.
"""

import os
import sys
import signal
import subprocess
import atexit
import time


def find_and_kill_zombie_mcp_processes():
    """
    Check for orphaned MCP-NixOS processes and terminate them.

    This behavior is controlled by the MCP_NIXOS_CLEANUP_ORPHANS environment variable.
    When set to "true", orphaned processes will be cleaned up. The default is "false".
    """
    # This is only supported on Unix/Linux/macOS
    if not hasattr(os, "popen"):
        return

    # Check if cleanup is enabled via environment variable
    cleanup_enabled = os.environ.get("MCP_NIXOS_CLEANUP_ORPHANS", "false").lower() == "true"
    if not cleanup_enabled:
        return

    try:
        # Look for any running python processes with mcp_nixos in the command line
        # but exclude ourself (exclude the run.py process)
        my_pid = os.getpid()
        proc = os.popen(
            f'ps -eo pid,command | grep "python.*mcp_nixos" | grep -v grep | grep -v run.py | grep -v "{my_pid}"'
        )
        lines = proc.readlines()
        proc.close()

        if lines:
            print(f"Found {len(lines)} potentially orphaned MCP-NixOS processes:")
            for line in lines:
                parts = line.split()
                if len(parts) > 1:
                    pid = parts[0]
                    try:
                        pid = int(pid)
                        if pid == my_pid:
                            continue  # Skip our own process

                        print(f"Killing orphaned process {pid}...")
                        # Try SIGTERM first
                        os.kill(pid, signal.SIGTERM)
                        # Wait a moment
                        time.sleep(0.1)
                        # Check if it's still alive
                        try:
                            os.kill(pid, 0)  # Signal 0 is a check if process exists
                            # If we get here, the process is still alive, use SIGKILL
                            print(f"Process {pid} still alive, using SIGKILL...")
                            os.kill(pid, signal.SIGKILL)
                        except OSError:
                            # Process is already gone, which is good
                            pass
                    except (ValueError, OSError, ProcessLookupError) as e:
                        print(f"Error killing process {pid}: {e}")
    except Exception as e:
        print(f"Error checking for orphaned processes: {e}")


def main():
    """
    Run the MCP-NixOS server in a way that guarantees clean termination.

    This function:
    1. Checks for and kills any orphaned MCP-NixOS processes
    2. Sets up signal handlers that will force clean termination
    3. Runs the MCP-NixOS server as a subprocess
    4. Ensures the subprocess is terminated when this script exits
    """

    # First, check for and kill any orphaned MCP-NixOS processes
    cleanup_enabled = os.environ.get("MCP_NIXOS_CLEANUP_ORPHANS", "false").lower() == "true"
    if cleanup_enabled:
        print("Starting MCP-NixOS server with enhanced termination handling...")
    else:
        print("Starting MCP-NixOS server (orphaned process cleanup disabled)...")
    find_and_kill_zombie_mcp_processes()
    # Store the server process
    server_process = None

    def cleanup_process():
        """Ensure the server process is terminated on exit with aggressive timeouts."""
        if server_process and server_process.poll() is None:
            try:
                # Try to terminate gracefully first
                print("Terminating server process...")
                server_process.terminate()
                # Give it only a very short time to terminate properly
                server_process.wait(timeout=0.5)  # Reduced timeout for more responsive feel
            except subprocess.TimeoutExpired:
                # Force kill immediately if it doesn't respond quickly
                print("Forcing immediate kill...")
                server_process.kill()
                try:
                    # Make one last attempt to wait for it to die
                    server_process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    print("Process is being stubborn, using most aggressive measures...")
                    # On POSIX systems, SIGKILL cannot be caught or ignored
                    try:
                        os.kill(server_process.pid, signal.SIGKILL)
                    except Exception as e:
                        print(f"Final kill attempt error: {e}")

    # Register the cleanup function to run on exit
    atexit.register(cleanup_process)

    def signal_handler(signum, frame):
        """Handle termination signals by cleaning up and immediately exiting."""
        signal_name = signal.Signals(signum).name
        print(f"\nReceived {signal_name}, terminating server...")

        # Kill the server process forcefully after logging
        if server_process and server_process.poll() is None:
            print("Killing server process...")
            # Immediately terminate the server process
            server_process.kill()

        # Exit immediately
        os._exit(130)  # Use os._exit to bypass any further Python cleanup

    # Set up signal handling
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal_handler)

    try:
        # Get the path to the MCP-NixOS module
        module_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Run the server as a subprocess
        cmd = [sys.executable, "-m", "mcp_nixos"]

        # Launch with unbuffered output so we can see logs in real time
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        # Starting message already printed above
        server_process = subprocess.Popen(
            cmd,
            env=env,
            cwd=module_path,
            # Don't capture outputs - let them go to our terminal
            stdout=None,
            stderr=None,
        )

        # Wait for the process to complete
        return_code = server_process.wait()

        # Process terminated on its own
        print(f"Server exited with code {return_code}")
        return return_code

    except KeyboardInterrupt:
        # This should be caught by our signal handler
        print("Server stopped by keyboard interrupt")
        return 0
    except Exception as e:
        print(f"Error running server: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
