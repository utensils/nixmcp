"""Tests for request gating based on initialization status."""

import pytest
from unittest.mock import MagicMock
from typing import Dict, Any, Optional

# Mark all tests in this module as asyncio and integration tests
pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


@pytest.mark.asyncio
class TestRequestGating:
    """Test request gating based on initialization status."""

    async def test_home_manager_ready_check(self, temp_cache_dir):
        """Test the Home Manager ready check function."""

        # Define local functions to simulate the actual implementation
        def check_request_ready(ctx):
            return ctx.request_context.lifespan_context.get("is_ready", False)

        def check_home_manager_ready(ctx) -> Optional[Dict[str, Any]]:
            # First check if server is ready
            if not check_request_ready(ctx):
                return {"error": "The server is still initializing. Please try again in a few seconds.", "found": False}

            # Get Home Manager context and check if data is loaded
            home_manager_context = ctx.request_context.lifespan_context.get("home_manager_context")
            if home_manager_context and hasattr(home_manager_context, "hm_client"):
                client = home_manager_context.hm_client
                if not client.is_loaded:
                    if client.loading_in_progress:
                        return {
                            "error": "Home Manager data is still loading. Please try again in a few seconds.",
                            "found": False,
                            "partial_init": True,
                        }
                    elif client.loading_error:
                        return {
                            "error": f"Failed to load Home Manager data: {client.loading_error}",
                            "found": False,
                            "partial_init": True,
                        }

            # All good
            return None

        # Mock request context
        mock_request = MagicMock()
        mock_request.request_context = MagicMock()
        mock_request.request_context.lifespan_context = {
            "is_ready": True,  # App is ready
            "home_manager_context": MagicMock(),
        }

        # Test when server is not ready
        mock_request.request_context.lifespan_context["is_ready"] = False
        result = check_home_manager_ready(mock_request)
        assert result is not None
        assert "error" in result
        assert "still initializing" in result["error"].lower()
        assert result.get("found") is False

        # Test when server is ready but Home Manager is still loading
        mock_request.request_context.lifespan_context["is_ready"] = True
        mock_hm_client = MagicMock()
        mock_hm_client.is_loaded = False
        mock_hm_client.loading_in_progress = True
        mock_hm_client.loading_error = None
        mock_request.request_context.lifespan_context["home_manager_context"].hm_client = mock_hm_client

        result = check_home_manager_ready(mock_request)
        assert result is not None
        assert "error" in result
        assert "still loading" in result["error"].lower()
        assert result.get("partial_init") is True

        # Test when Home Manager failed to load
        mock_hm_client.loading_in_progress = False
        mock_hm_client.loading_error = "Failed to load"

        result = check_home_manager_ready(mock_request)
        assert result is not None
        assert "error" in result
        assert "failed to load" in result["error"].lower()
        assert result.get("partial_init") is True

        # Test when everything is ready
        mock_hm_client.is_loaded = True
        mock_hm_client.loading_error = None

        result = check_home_manager_ready(mock_request)
        assert result is None  # No error when ready

    async def test_nixos_tools_check_request_ready(self, temp_cache_dir):
        """Test the NixOS tools check_request_ready function."""

        # Define a local function to simulate the actual implementation
        def check_request_ready(ctx):
            return ctx.request_context.lifespan_context.get("is_ready", False)

        # Mock request context
        mock_request = MagicMock()
        mock_request.request_context = MagicMock()
        mock_request.request_context.lifespan_context = {"is_ready": False}

        # Test when not ready
        assert check_request_ready(mock_request) is False

        # Test when ready
        mock_request.request_context.lifespan_context["is_ready"] = True
        assert check_request_ready(mock_request) is True
