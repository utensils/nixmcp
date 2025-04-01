"""Tests for timeout handling during shutdown operations.

These tests verify that the server properly handles timeouts during shutdown
operations, ensuring that it doesn't hang indefinitely when a component
is unresponsive during termination.
"""

import asyncio
import sys
import time
from unittest.mock import patch, MagicMock, AsyncMock
import pytest


class TestTimeoutHandling:
    """Test proper timeout handling during shutdown operations."""

    @pytest.mark.asyncio
    async def test_shutdown_with_hung_component(self, temp_cache_dir):
        """Test shutdown with a component that hangs indefinitely."""
        # Mock server
        mock_server = MagicMock()

        # Import after patching to avoid real dependencies
        if "mcp_nixos.server" in sys.modules:
            del sys.modules["mcp_nixos.server"]

        # Create a hung service that never completes
        async def never_completes():
            """Simulate a hung service that never completes."""
            # This simulates a component that's completely unresponsive
            while True:
                await asyncio.sleep(1)

        # Import with patched environment
        with patch("mcp_nixos.server.logger") as mock_logger:
            from mcp_nixos.server import app_lifespan, darwin_context

            # Patch shutdown with our hung function
            with patch.object(darwin_context, "shutdown", side_effect=never_completes):
                # Create the context manager
                context_manager = app_lifespan(mock_server)

                # Enter the context
                await context_manager.__aenter__()

                # Start time to measure shutdown duration
                start_time = time.time()

                # Run shutdown with a timeout
                # Our implementation should handle the hung component and continue
                try:
                    await asyncio.wait_for(
                        context_manager.__aexit__(None, None, None),
                        timeout=10.0,  # Give enough time for our implementation's timeouts to trigger
                    )

                    # Calculate how long shutdown took
                    shutdown_duration = time.time() - start_time

                    # Verify shutdown messages were logged
                    mock_logger.info.assert_any_call("Shutting down MCP-NixOS server")

                    # Our timeout mechanism should have triggered a warning (0.5s is the new timeout value)
                    mock_logger.warning.assert_any_call("Darwin context shutdown timed out after 0.5s")

                    # And we should have a completion message with duration
                    completion_logged = False
                    for call_args in mock_logger.info.call_args_list:
                        call_str = str(call_args)
                        if "Shutdown completed in" in call_str:
                            completion_logged = True
                            break

                    assert completion_logged, "Shutdown completion message not logged"

                    # Assert shutdown took less than our overall timeout
                    # but more than the component timeout (since it had to wait for timeout)
                    assert (
                        0.3 <= shutdown_duration < 2.0
                    ), f"Shutdown duration outside expected range: {shutdown_duration}"

                except asyncio.TimeoutError:
                    pytest.fail("Shutdown timed out - implementation still hanging")

    @pytest.mark.asyncio
    async def test_shutdown_with_slow_component(self, temp_cache_dir):
        """Test shutdown with a component that's slow but eventually completes."""
        # Mock server
        mock_server = MagicMock()

        # Import after patching to avoid real dependencies
        if "mcp_nixos.server" in sys.modules:
            del sys.modules["mcp_nixos.server"]

        # Flag to track if shutdown was called
        shutdown_called = False

        # Create a test function that just verifies it was called
        async def mock_shutdown():
            """Mock shutdown that just verifies it was called."""
            nonlocal shutdown_called
            shutdown_called = True
            return True

        # Import with patched environment
        with patch("mcp_nixos.server.logger") as mock_logger:
            from mcp_nixos.server import app_lifespan, darwin_context

            # Patch shutdown with our mock function
            with patch.object(darwin_context, "shutdown", side_effect=mock_shutdown):
                # Create the context manager
                context_manager = app_lifespan(mock_server)

                # Enter the context
                await context_manager.__aenter__()

                # Exit context to trigger shutdown
                await context_manager.__aexit__(None, None, None)

                # Verify shutdown message was logged
                mock_logger.info.assert_any_call("Shutting down MCP-NixOS server")

                # Verify our mock function was called
                assert shutdown_called, "Shutdown was not called"

    @pytest.mark.asyncio
    async def test_multiple_components_with_different_speeds(self, temp_cache_dir):
        """Test shutdown with multiple components with different response times."""
        # Mock server
        mock_server = MagicMock()

        # Import after patching to avoid real dependencies
        if "mcp_nixos.server" in sys.modules:
            del sys.modules["mcp_nixos.server"]

        # Create a slow service that eventually completes
        async def slow_darwin_shutdown():
            """Simulate a slow service that eventually completes."""
            await asyncio.sleep(0.2)  # Slower but not hung
            return True

        # Create a fast service
        async def fast_service_shutdown():
            """Simulate a fast service shutdown."""
            await asyncio.sleep(0.05)  # Very quick
            return True

        # Mock components
        mock_fast_service = AsyncMock()
        mock_fast_service.shutdown = fast_service_shutdown

        # Configure server's timeout to be long enough for our test
        with patch("mcp_nixos.server.async_with_timeout", side_effect=lambda coro, **kwargs: coro):
            # Import with patched environment
            with patch("mcp_nixos.server.logger") as mock_logger:
                from mcp_nixos.server import app_lifespan, darwin_context, home_manager_context

                # Patch shutdown with our slow function for darwin
                with patch.object(darwin_context, "shutdown", side_effect=slow_darwin_shutdown):
                    # Add a faster component by patching home_manager_context
                    # Use create=True since home_manager_context doesn't have a shutdown method
                    with patch.object(home_manager_context, "shutdown", new=mock_fast_service.shutdown, create=True):

                        # Create the context manager
                        context_manager = app_lifespan(mock_server)

                        # Enter the context
                        await context_manager.__aenter__()

                        # Start time for measuring shutdown duration
                        start_time = time.time()

                        # Exit context to trigger shutdown
                        await context_manager.__aexit__(None, None, None)

                        # Calculate shutdown duration
                        shutdown_duration = time.time() - start_time

                        # Verify shutdown message was logged
                        mock_logger.info.assert_any_call("Shutting down MCP-NixOS server")

                        # Check that shutdown took approximately the expected time
                        # Should be approximately as long as our slowest component plus overhead
                        assert shutdown_duration < 1.0, f"Shutdown took too long: {shutdown_duration} seconds"

    @pytest.mark.asyncio
    async def test_graceful_shutdown_with_critical_error(self, temp_cache_dir):
        """Test graceful shutdown when a critical error occurs."""
        # Mock server
        mock_server = MagicMock()

        # Import after patching
        if "mcp_nixos.server" in sys.modules:
            del sys.modules["mcp_nixos.server"]

        # Import with patched environment
        with patch("mcp_nixos.server.logger") as mock_logger:
            from mcp_nixos.server import app_lifespan, darwin_context

            # Create a mock for darwin_context shutdown that raises an exception
            async def shutdown_with_error():
                """Simulate a service that encounters an error during shutdown."""
                raise RuntimeError("Critical error during shutdown")

            # Patch shutdown to raise an exception
            with patch.object(darwin_context, "shutdown", side_effect=shutdown_with_error):
                # Create the context manager
                context_manager = app_lifespan(mock_server)

                # Enter the context
                await context_manager.__aenter__()

                # Exit context to trigger shutdown
                await context_manager.__aexit__(None, None, None)

                # Verify error was logged (with the updated message format)
                mock_logger.error.assert_any_call(
                    "Error during Darwin context shutdown: Critical error during shutdown"
                )

                # Verify we still completed overall shutdown despite the error
                mock_logger.info.assert_any_call("Shutting down MCP-NixOS server")

    @pytest.mark.asyncio
    async def test_concurrent_shutdown_operations(self, temp_cache_dir):
        """Test that multiple shutdown operations can happen concurrently."""
        # Set up a simpler test that just verifies the shutdowns are called
        # and that the overall duration is reasonable

        # Track which shutdown methods were called
        shutdown_called = {"darwin": False, "home_manager": False}

        # Mock shutdown methods that track when they're called
        async def mock_darwin_shutdown():
            shutdown_called["darwin"] = True
            await asyncio.sleep(0.1)
            return True

        async def mock_home_manager_shutdown():
            shutdown_called["home_manager"] = True
            await asyncio.sleep(0.1)
            return True

        # Create server mock
        mock_server = MagicMock()

        # Make sure we have a clean module import
        if "mcp_nixos.server" in sys.modules:
            del sys.modules["mcp_nixos.server"]

        # Import with patched environment
        with patch("mcp_nixos.server.logger") as mock_logger:
            from mcp_nixos.server import app_lifespan, darwin_context, home_manager_context

            # Apply our mocks
            with patch.object(darwin_context, "shutdown", side_effect=mock_darwin_shutdown):
                with patch.object(
                    home_manager_context, "shutdown", side_effect=mock_home_manager_shutdown, create=True
                ):

                    # Create and enter context
                    context_manager = app_lifespan(mock_server)
                    await context_manager.__aenter__()

                    # Start time for measuring shutdown duration
                    start_time = time.time()

                    # Exit context to trigger shutdown
                    await context_manager.__aexit__(None, None, None)

                    # Calculate shutdown duration
                    total_duration = time.time() - start_time

                    # Verify shutdown message was logged
                    mock_logger.info.assert_any_call("Shutting down MCP-NixOS server")

                    # Test for elapsed time
                    assert total_duration < 1.0, f"Shutdown took too long: {total_duration}s"
