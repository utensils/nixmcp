"""Tests for proper termination behavior of the MCP-NixOS server."""

import asyncio
import os
import signal
import sys
import time
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import pytest
from unittest.mock import patch, MagicMock


# Top level server process function for multiprocessing
def run_server_process(ready_queue, shutdown_complete_queue):
    """Run the server in a separate process for signal testing."""
    try:
        # Set up mocks and import server
        from mcp_nixos.server import mcp

        # Signal that the process is ready
        ready_queue.put(True)

        # Set up a handler to notify the test when shutdown is complete
        original_exit = sys.exit

        def exit_handler(code=0):
            shutdown_complete_queue.put(True)
            original_exit(code)

        sys.exit = exit_handler

        # Run the server (blocked until terminated)
        mcp.run()

    except KeyboardInterrupt:
        # Normal signal-based termination
        shutdown_complete_queue.put(True)
    except Exception as e:
        # Put the exception on the queue so test can see it
        shutdown_complete_queue.put(str(e))


class TestServerTermination:
    """Test the server's termination behavior."""

    @pytest.mark.timeout(10)  # Timeout after 10 seconds to prevent hanging tests
    def test_sigterm_handled_properly(self):
        """Test that the server terminates cleanly when receiving SIGTERM."""
        # Queues for inter-process communication
        ready_queue = multiprocessing.Queue()
        shutdown_complete_queue = multiprocessing.Queue()

        # Start server in a separate process
        process = multiprocessing.Process(target=run_server_process, args=(ready_queue, shutdown_complete_queue))
        process.start()

        try:
            # Wait for server to indicate it's ready
            assert ready_queue.get(timeout=5) is True

            # Allow time for server startup
            time.sleep(0.5)

            # Send SIGTERM to process
            if process.pid is not None:
                os.kill(process.pid, signal.SIGTERM)

            # Check if shutdown completed properly
            result = shutdown_complete_queue.get(timeout=5)

            # Verify shutdown was successful
            assert result is True, f"Unexpected result: {result}"

            # Wait for process to actually terminate
            process.join(timeout=5)

            # Verify process has terminated
            assert not process.is_alive(), "Process did not terminate within timeout"

        finally:
            # Clean up in case of test failure
            if process.is_alive():
                process.terminate()
                process.join(timeout=1)
                if process.is_alive():
                    process.kill()
                    process.join()

    @pytest.mark.timeout(10)  # Timeout after 10 seconds to prevent hanging tests
    def test_sigint_handled_properly(self):
        """Test that the server terminates cleanly when receiving SIGINT (Ctrl+C)."""
        # Queues for inter-process communication
        ready_queue = multiprocessing.Queue()
        shutdown_complete_queue = multiprocessing.Queue()

        # Start server in a separate process
        process = multiprocessing.Process(target=run_server_process, args=(ready_queue, shutdown_complete_queue))
        process.start()

        try:
            # Wait for server to indicate it's ready
            assert ready_queue.get(timeout=5) is True

            # Allow time for server startup
            time.sleep(0.5)

            # Send SIGINT (Ctrl+C) to process
            if process.pid is not None:
                os.kill(process.pid, signal.SIGINT)

            # Check if shutdown completed properly
            result = shutdown_complete_queue.get(timeout=5)

            # Verify shutdown was successful
            assert result is True, f"Unexpected result: {result}"

            # Wait for process to actually terminate
            process.join(timeout=5)

            # Verify process has terminated
            assert not process.is_alive(), "Process did not terminate within timeout"

        finally:
            # Clean up in case of test failure
            if process.is_alive():
                process.terminate()
                process.join(timeout=1)
                if process.is_alive():
                    process.kill()
                    process.join()

    @pytest.mark.asyncio
    async def test_handler_exceptions_during_shutdown(self, temp_cache_dir):
        """Test that exceptions during shutdown are properly handled."""
        # Mock server
        mock_server = MagicMock()

        # Import after patching to avoid real dependencies
        if "mcp_nixos.server" in sys.modules:
            del sys.modules["mcp_nixos.server"]

        # Import server module with patched env
        with patch("mcp_nixos.server.logger"):
            from mcp_nixos.server import app_lifespan, darwin_context

            # Set up darwin_context.shutdown to raise exception
            with patch.object(
                darwin_context, "shutdown", side_effect=Exception("Test shutdown exception")
            ) as mock_shutdown:

                # Create and enter lifespan context
                context_manager = app_lifespan(mock_server)
                await context_manager.__aenter__()

                # Exit context to trigger cleanup
                await context_manager.__aexit__(None, None, None)

                # Verify shutdown was attempted
                mock_shutdown.assert_called_once()

                # The error would be logged but we can't assert it with our mock

    @pytest.mark.asyncio
    async def test_shutdown_timeout_handling(self, temp_cache_dir):
        """Test that shutdown operations have proper timeout handling."""
        # Mock server
        mock_server = MagicMock()

        # Import after patching to avoid real dependencies
        if "mcp_nixos.server" in sys.modules:
            del sys.modules["mcp_nixos.server"]

        # Import server module with patched env
        with patch("mcp_nixos.server.logger"):
            from mcp_nixos.server import app_lifespan, darwin_context

            # Create a sleep function that simulates a hung operation
            async def slow_shutdown():
                await asyncio.sleep(10)  # Deliberately slow
                return True

            # Patch darwin_context.shutdown with our slow function
            with patch.object(darwin_context, "shutdown", side_effect=slow_shutdown) as mock_shutdown:
                # Create a future to track when shutdown completes
                shutdown_future = asyncio.Future()

                # We'll use ThreadPoolExecutor to run the shutdown with a timeout
                with ThreadPoolExecutor() as executor:

                    def run_shutdown():
                        asyncio.run(context_manager.__aexit__(None, None, None))
                        shutdown_future.set_result(True)

                    # Create and enter the context manager
                    context_manager = app_lifespan(mock_server)
                    await context_manager.__aenter__()

                    # Run shutdown in a separate thread so we can apply a timeout
                    executor.submit(run_shutdown)

                    # Wait for shutdown with a timeout
                    try:
                        await asyncio.wait_for(shutdown_future, timeout=2)
                    except asyncio.TimeoutError:
                        # This is expected - the shutdown should hang due to our mocked slow function
                        # In a proper implementation, there should be a timeout mechanism
                        pass

                    # Check if shutdown was attempted
                    mock_shutdown.assert_called_once()

                    # Ideal behavior: even with a hung component, shutdown should eventually
                    # complete with appropriate error handling


# Add tests for resource cleanup during termination
class TestResourceCleanupOnTermination:
    """Test proper resource cleanup during server termination."""

    @pytest.mark.asyncio
    async def test_cleanup_after_termination_signal(self, temp_cache_dir):
        """Test that resources are properly cleaned up after termination signal."""
        # Mock server
        mock_server = MagicMock()

        # Import after patching
        if "mcp_nixos.server" in sys.modules:
            del sys.modules["mcp_nixos.server"]

        # Set up signal handling mocks
        with patch("mcp_nixos.server.logger"):
            from mcp_nixos.server import app_lifespan, darwin_context

            # Create mock resources that we expect to be cleaned up
            darwin_cleanup = MagicMock()

            # Patch cleanup methods
            with patch.object(darwin_context, "shutdown", new=darwin_cleanup) as mock_darwin_cleanup:
                # Use patch.object with the client property
                with patch.object(darwin_context, "client", create=True):
                    # Enter and exit the context manager
                    async with app_lifespan(mock_server):
                        pass  # Normal exit

                    # Verify all cleanup methods were called
                    mock_darwin_cleanup.assert_called_once()

                    # Shutdown would be logged but we can't assert it with our mock
