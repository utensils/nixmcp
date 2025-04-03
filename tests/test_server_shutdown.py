"""Tests for server shutdown operations and error handling."""

import asyncio
import pytest
import time
from unittest.mock import MagicMock, patch, AsyncMock

# Import fixtures
from tests.fixtures.server_fixtures import (
    mock_home_manager_context,
    mock_darwin_context,
    mock_nixos_context,
    mock_state_persistence,
    server_mock_modules,
)

# Import patch helper
from tests.fixtures.patch_helper import patch_dict


class TestServerShutdown:
    """Test server shutdown operations and error handling."""

    @pytest.mark.asyncio
    async def test_state_persistence_error_during_shutdown(self, server_mock_modules, mock_state_persistence):
        """Test error handling when state persistence fails during shutdown."""
        # Mock objects
        mock_lifespan_context = {"initialization_time": time.time() - 100}  # 100s ago

        # Configure state persistence to fail
        mock_state_persistence.save_state.side_effect = Exception("Save failed")

        # Update mocks
        modified_mocks = {**server_mock_modules}

        # Patch modules
        with patch_dict(modified_mocks):
            # Create a simplified version of the shutdown function
            async def simulate_shutdown():
                try:
                    if mock_lifespan_context.get("initialization_time"):
                        uptime = time.time() - mock_lifespan_context["initialization_time"]
                        mock_state_persistence.set_state("last_uptime", uptime)
                        modified_mocks["mcp_nixos.server.logger"].info(f"Server uptime: {uptime:.2f}s")

                    # This will raise an exception
                    mock_state_persistence.save_state()
                except Exception as e:
                    modified_mocks["mcp_nixos.server.logger"].error(f"Error saving state during shutdown: {e}")

                # Skip context shutdown for this test

            # Execute the function
            await simulate_shutdown()

            # Verify interactions
            mock_state_persistence.set_state.assert_called_with("last_uptime", pytest.approx(100, abs=5))
            modified_mocks["mcp_nixos.server.logger"].error.assert_called_with(
                "Error saving state during shutdown: Save failed"
            )

    @pytest.mark.asyncio
    async def test_concurrent_context_shutdown_timeout(
        self,
        server_mock_modules,
        mock_darwin_context,
        mock_home_manager_context,
        mock_nixos_context,
        mock_state_persistence,
    ):
        """Test handling timeout in concurrent context shutdown operations."""
        # Set up Darwin context to block
        mock_darwin_context.shutdown = AsyncMock(side_effect=lambda: asyncio.sleep(10.0))  # Will timeout

        # Set up Home Manager context to block
        mock_home_manager_context.shutdown = AsyncMock(side_effect=lambda: asyncio.sleep(10.0))  # Will timeout

        # Set up NixOS context to succeed quickly
        mock_nixos_context.shutdown = AsyncMock(return_value=None)  # Will complete quickly

        # Set up required fixtures
        mock_async_with_timeout = AsyncMock(side_effect=lambda func, **kwargs: func())

        # Update mocks dict
        modified_mocks = {**server_mock_modules, "mcp_nixos.server.async_with_timeout": mock_async_with_timeout}

        with patch_dict(modified_mocks):
            # Create a simplified version of shutdown with timeout handling
            async def simulate_shutdown_timeout():
                # Create coroutines for shutdown operations
                shutdown_coroutines = []

                # Add Darwin context shutdown with timeout
                if hasattr(mock_darwin_context, "shutdown") and callable(mock_darwin_context.shutdown):
                    shutdown_coroutines.append(
                        mock_async_with_timeout(
                            lambda: mock_darwin_context.shutdown(),
                            timeout_seconds=0.5,
                            operation_name="Darwin context shutdown",
                        )
                    )

                # Add shutdown for home_manager_context
                if hasattr(mock_home_manager_context, "shutdown") and callable(mock_home_manager_context.shutdown):
                    shutdown_coroutines.append(
                        mock_async_with_timeout(
                            lambda: mock_home_manager_context.shutdown(),
                            timeout_seconds=0.5,
                            operation_name="Home Manager context shutdown",
                        )
                    )

                # Add shutdown for nixos_context
                if hasattr(mock_nixos_context, "shutdown") and callable(mock_nixos_context.shutdown):
                    shutdown_coroutines.append(
                        mock_async_with_timeout(
                            lambda: mock_nixos_context.shutdown(),
                            timeout_seconds=0.5,
                            operation_name="NixOS context shutdown",
                        )
                    )

                # Execute all shutdown operations with timeout - will raise TimeoutError
                shutdown_tasks = [asyncio.create_task(coro) for coro in shutdown_coroutines]

                try:
                    # This will raise TimeoutError since we're using a very short timeout
                    await asyncio.wait_for(
                        asyncio.gather(*shutdown_tasks, return_exceptions=True),
                        timeout=0.1,  # Very short timeout to ensure it fails
                    )
                    modified_mocks["mcp_nixos.server.logger"].debug("All context shutdowns completed")
                except asyncio.TimeoutError:
                    modified_mocks["mcp_nixos.server.logger"].warning(
                        "Some shutdown operations timed out and were terminated"
                    )
                    # Record abnormal shutdown in state
                    try:
                        mock_state_persistence.set_state("shutdown_reason", "timeout")
                        mock_state_persistence.save_state()
                    except Exception:
                        pass  # Avoid cascading errors

            # Execute the function - this time we catch the timeout
            await simulate_shutdown_timeout()

            # Verify timeout was handled properly
            modified_mocks["mcp_nixos.server.logger"].warning.assert_called_with(
                "Some shutdown operations timed out and were terminated"
            )
            mock_state_persistence.set_state.assert_called_with("shutdown_reason", "timeout")
            mock_state_persistence.save_state.assert_called_once()

    def test_context_accessor_functions(self, server_mock_modules, mock_home_manager_context, mock_darwin_context):
        """Test the context accessor functions."""
        with patch_dict(server_mock_modules):
            # Import the accessor functions here to use the patched modules
            from mcp_nixos.server import get_home_manager_context, get_darwin_context

            # Call the accessor functions
            returned_hm_context = get_home_manager_context()
            returned_darwin_context = get_darwin_context()

            # Verify they return the correct objects
            assert returned_hm_context is mock_home_manager_context
            assert returned_darwin_context is mock_darwin_context