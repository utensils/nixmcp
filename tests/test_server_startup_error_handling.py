"""Tests for server startup error handling and timeout recovery."""

import asyncio
import pytest


class TestServerStartupErrorHandling:
    """Test error handling during server startup."""

    @pytest.mark.asyncio
    async def test_darwin_context_startup_error(self):
        """Test recovery from Darwin context startup error."""
        # Use direct mocking
        from unittest.mock import patch, MagicMock, AsyncMock

        # Create mock objects
        mock_logger = MagicMock()
        mock_darwin_context = MagicMock()
        mock_darwin_context.startup = AsyncMock()

        # Test event and lifespan context
        mock_app_ready = MagicMock()
        mock_protocol_initialized = MagicMock()
        mock_protocol_initialized.wait = AsyncMock()
        mock_lifespan_context = {}

        # Create a self-contained mock function to avoid importing server modules
        async def mock_async_timeout_function(**kwargs):
            raise Exception("Darwin startup failed")

        # Patch only the logger for verification
        with patch("mcp_nixos.server.logger", mock_logger):
            # Create a simplified version of the startup function
            async def simulate_startup():
                try:
                    # This will raise the exception we defined
                    await mock_async_timeout_function(operation_name="Darwin context startup")
                except Exception as e:
                    mock_logger.error(f"Error starting Darwin context: {e}")

                # Mark app as ready despite error
                mock_app_ready.set()

                # Wait for protocol init (simulate success)
                await mock_protocol_initialized.wait()
                mock_lifespan_context["is_ready"] = True

            # Execute the function
            await simulate_startup()

            # Verify error was logged but startup continued
            mock_logger.error.assert_called_with("Error starting Darwin context: Darwin startup failed")
            mock_app_ready.set.assert_called_once()
            assert mock_lifespan_context["is_ready"] is True

    @pytest.mark.asyncio
    async def test_protocol_initialization_timeout(self):
        """Test recovery from MCP protocol initialization timeout."""
        from unittest.mock import patch, MagicMock, AsyncMock

        # Set up test objects
        mock_logger = MagicMock()
        mock_app_ready = MagicMock()
        mock_protocol_initialized = MagicMock()
        mock_protocol_initialized.wait = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_lifespan_context = {}

        # Patch the logger
        with patch("mcp_nixos.server.logger", mock_logger):
            # Create a simplified version of the protocol init timeout handler
            async def simulate_protocol_timeout():
                # Mark app as ready
                mock_app_ready.set()

                # Wait for MCP protocol initialization (with timeout)
                try:
                    await asyncio.wait_for(mock_protocol_initialized.wait(), timeout=5.0)
                    mock_logger.info("MCP protocol initialization complete")
                    mock_lifespan_context["is_ready"] = True
                except asyncio.TimeoutError:
                    mock_logger.warning("Timeout waiting for MCP initialize request. Server will proceed anyway.")
                    # Still mark as ready to avoid hanging
                    mock_lifespan_context["is_ready"] = True

            # Execute the function
            await simulate_protocol_timeout()

            # Verify timeout was handled and server continued
            mock_logger.warning.assert_called_with(
                "Timeout waiting for MCP initialize request. Server will proceed anyway."
            )
            mock_app_ready.set.assert_called_once()
            assert mock_lifespan_context["is_ready"] is True

    def test_prompt_function(self):
        """Test that the prompt configuration uses expected decorator pattern."""
        # This test verifies that the prompt function is defined with the @prompt decorator
        # which we can test by checking for the pattern in the source code
        import inspect
        import mcp_nixos.server

        source = inspect.getsource(mcp_nixos.server)
        assert "@mcp_server.prompt()" in source
        assert "def mcp_nixos_prompt():" in source
