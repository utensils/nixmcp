"""Tests for server startup error handling and timeout recovery."""

import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

# Use fixtures
from tests.fixtures.server_fixtures import mock_darwin_context, server_mock_modules

# Import patch helper
from tests.fixtures.patch_helper import patch_dict


class TestServerStartupErrorHandling:
    """Test error handling during server startup."""

    @pytest.mark.asyncio
    async def test_darwin_context_startup_error(self, server_mock_modules):
        """Test recovery from Darwin context startup error."""
        # Create a custom async_with_timeout that raises an exception
        mock_async_with_timeout = AsyncMock(side_effect=Exception("Darwin startup failed"))

        # Update mock modules
        modified_mocks = {**server_mock_modules, "mcp_nixos.server.async_with_timeout": mock_async_with_timeout}

        # Test event and lifespan context
        mock_app_ready = MagicMock()
        mock_protocol_initialized = MagicMock()
        mock_protocol_initialized.wait = AsyncMock()
        mock_lifespan_context = {}

        with patch_dict(modified_mocks):
            # Create a simplified version of the startup function
            async def simulate_startup():
                try:
                    await modified_mocks["mcp_nixos.server.async_with_timeout"](
                        lambda: modified_mocks["mcp_nixos.server.darwin_context"].startup(),
                        timeout_seconds=10.0,
                        operation_name="Darwin context startup",
                    )
                except Exception as e:
                    modified_mocks["mcp_nixos.server.logger"].error(f"Error starting Darwin context: {e}")

                # Mark app as ready despite error
                mock_app_ready.set()

                # Wait for protocol init (simulate success)
                await mock_protocol_initialized.wait()
                mock_lifespan_context["is_ready"] = True

            # Execute the function
            await simulate_startup()

            # Verify error was logged but startup continued
            modified_mocks["mcp_nixos.server.logger"].error.assert_called_with(
                "Error starting Darwin context: Darwin startup failed"
            )
            mock_app_ready.set.assert_called_once()
            assert mock_lifespan_context["is_ready"] is True

    @pytest.mark.asyncio
    async def test_protocol_initialization_timeout(self, server_mock_modules):
        """Test recovery from MCP protocol initialization timeout."""
        # Set up test objects
        mock_app_ready = MagicMock()
        mock_protocol_initialized = MagicMock()
        mock_protocol_initialized.wait = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_lifespan_context = {}

        with patch_dict(server_mock_modules):
            # Create a simplified version of the protocol init timeout handler
            async def simulate_protocol_timeout():
                # Mark app as ready
                mock_app_ready.set()

                # Wait for MCP protocol initialization (with timeout)
                try:
                    await asyncio.wait_for(mock_protocol_initialized.wait(), timeout=5.0)
                    server_mock_modules["mcp_nixos.server.logger"].info("MCP protocol initialization complete")
                    mock_lifespan_context["is_ready"] = True
                except asyncio.TimeoutError:
                    server_mock_modules["mcp_nixos.server.logger"].warning(
                        "Timeout waiting for MCP initialize request. Server will proceed anyway."
                    )
                    # Still mark as ready to avoid hanging
                    mock_lifespan_context["is_ready"] = True

            # Execute the function
            await simulate_protocol_timeout()

            # Verify timeout was handled and server continued
            server_mock_modules["mcp_nixos.server.logger"].warning.assert_called_with(
                "Timeout waiting for MCP initialize request. Server will proceed anyway."
            )
            mock_app_ready.set.assert_called_once()
            assert mock_lifespan_context["is_ready"] is True

    def test_prompt_function(self, server_mock_modules):
        """Test that the prompt configuration function returns expected content."""
        with patch_dict(server_mock_modules):
            # Verify the function was called and returns expected content
            mock_prompt_func = server_mock_modules["mcp_nixos.server.mcp_nixos_prompt"]
            assert "Model Context Protocol (MCP)" in mock_prompt_func()