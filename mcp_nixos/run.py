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
from typing import Optional

# Global server process variable that will be set in main() and used in signal_handler
server_process: Optional[subprocess.Popen] = None


def find_and_kill_zombie_mcp_processes():
    """
    Check for orphaned MCP-NixOS processes and terminate them.

    This behavior is controlled by the MCP_NIXOS_CLEANUP_ORPHANS environment variable.
    When set to "true", orphaned processes will be cleaned up. The default is "false".
    """
    # Check if cleanup is enabled via environment variable
    cleanup_enabled = os.environ.get("MCP_NIXOS_CLEANUP_ORPHANS", "false").lower() == "true"
    if not cleanup_enabled:
        return

    try:
        import psutil

        my_pid = os.getpid()
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                # Skip our own process
                if proc.pid == my_pid:
                    continue

                # Look for python processes running mcp_nixos
                proc_name = proc.name().lower()
                if proc_name.startswith("python"):
                    cmdline = " ".join(proc.cmdline()) if proc.cmdline() else ""
                    if "mcp_nixos" in cmdline and "run.py" not in cmdline:
                        print(f"Found orphaned process {proc.pid}: {cmdline}")
                        proc.terminate()
                        # Wait briefly
                        try:
                            proc.wait(timeout=0.5)
                        except psutil.TimeoutExpired:
                            print(f"Process {proc.pid} not responding, using kill...")
                            proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
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
        import sys  # Make sure sys is imported

        try:
            signal_name = signal.Signals(signum).name
        except ValueError:
            signal_name = f"UNKNOWN({signum})"

        print(f"\n⚠️ SIGNAL: Received {signal_name}, terminating server...")

        # Log more details about the signal and the current state
        import traceback

        stack_trace = "".join(traceback.format_stack(frame))
        print(f"Signal occurred during execution at:\n{stack_trace}")

        # Get detailed process information for debugging
        try:
            import psutil
            import os

            # Log information about our wrapper process
            wrapper_process = psutil.Process()
            print(f"Wrapper process - PID: {wrapper_process.pid}, Status: {wrapper_process.status()}")

            # Log information about server subprocess
            if server_process:
                try:
                    sp_pid = server_process.pid
                    sp = psutil.Process(sp_pid)
                    print(
                        f"Server process - PID: {sp_pid}, Status: {sp.status()}, "
                        f"Running: {server_process.poll() is None}"
                    )
                    print(f"Server CPU: {sp.cpu_percent()}%, Memory: {sp.memory_info().rss / (1024*1024):.1f}MB")

                    # Check if server process has children that might be causing issues
                    children = sp.children(recursive=True)
                    if children:
                        print(f"Server has {len(children)} child processes:")
                        for child in children:
                            try:
                                print(f"  Child - PID: {child.pid}, Name: {child.name()}, Status: {child.status()}")
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                print(f"  Child - PID: {child.pid}, Info unavailable")
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    print(f"Error accessing server process info: {e}")

            # Check for Windsurf or other MCP client environment variables
            windsurf_vars = [var for var in os.environ if "WINDSURF" in var.upper() or "WINDSURFER" in var.upper()]
            if windsurf_vars:
                print("Running under Windsurf environment:")
                for var in windsurf_vars:
                    print(f"  {var}={os.environ[var]}")
        except Exception as e:
            print(f"Error getting process details: {e}")

        # Kill the server process forcefully after logging
        if server_process and server_process.poll() is None:
            print(f"Killing server process {server_process.pid}...")
            # Immediately terminate the server process
            try:
                server_process.kill()
                print(f"Kill signal sent to PID {server_process.pid}")
                # Optionally wait briefly for confirmation
                try:
                    server_process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    print("Server process kill confirmation timed out.")
            except Exception as e:
                print(f"Error killing server process: {e}")
                # Try alternative kill method if standard method fails
                try:
                    os.kill(server_process.pid, signal.SIGKILL)
                    print(f"SIGKILL sent to PID {server_process.pid} via os.kill")
                except Exception as e2:
                    print(f"Failed to kill via os.kill: {e2}")

        # Exit with sys.exit instead of os._exit for cleaner exit
        print("Exiting wrapper process...")
        sys.exit(130)  # Use sys.exit for cleaner exit signaling interrupted state

    # Set up signal handling (Windows-compatible)
    if sys.platform == "win32":
        # Windows doesn't support all the same signals
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Safe Windows-specific handling for CTRL events
        win32api_available = False
        try:
            # Try to import win32api safely
            import importlib.util

            if importlib.util.find_spec("win32api") is not None:
                import win32api

                # Only set the handler if the module is properly loaded and functioning
                if hasattr(win32api, "SetConsoleCtrlHandler"):
                    win32api.SetConsoleCtrlHandler(
                        lambda ctrl_type: signal_handler(signal.SIGINT, None) if ctrl_type == 0 else None, True
                    )
                    win32api_available = True
        except (ImportError, AttributeError) as e:
            # Specific error handling
            print(f"Warning: Enhanced Windows CTRL event handling unavailable: {e}")
            pass

        if not win32api_available:
            print("Note: Using basic signal handling for Windows. Install pywin32 for enhanced handling.")
    else:
        # Unix signals
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
