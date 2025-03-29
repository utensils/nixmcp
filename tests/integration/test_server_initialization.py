"""Integration test for server initialization and cache directory creation."""

import os
import pathlib
import pytest
import sys
from unittest.mock import patch, MagicMock

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


def test_server_initializes_cache_directory(temp_cache_dir):
    """Test that the server properly initializes the cache directory during startup."""
    # Create a specific test cache path under our controlled temp directory
    cache_path = pathlib.Path(temp_cache_dir) / "server_init_test_cache"

    # Set environment variable to use our test directory
    with patch.dict(os.environ, {"MCP_NIXOS_CACHE_DIR": str(cache_path)}):
        # We need to reload the server module to use our environment variable
        # Remove the module if it's already loaded
        if "mcp_nixos.server" in sys.modules:
            del sys.modules["mcp_nixos.server"]

        # Now import the module, which will create our cache directory
        import mcp_nixos.server  # noqa: F401

        # Verify that the cache directory was created
        assert cache_path.exists()
        assert cache_path.is_dir()

        # Test to make sure the directory has proper permissions (on Unix)
        if sys.platform != "win32":
            assert oct(cache_path.stat().st_mode)[-3:] == "700"


@pytest.mark.asyncio
async def test_server_startup_with_fallback_cache(temp_cache_dir):
    """Test that the server falls back to a temporary directory when cache creation fails."""
    # Create a patch to force a permission error during cache directory creation
    with patch("mcp_nixos.utils.cache_helpers.ensure_cache_dir") as mock_ensure_dir:
        mock_ensure_dir.side_effect = PermissionError("Permission denied creating cache directory")

        # We need to reload the server module to use our mocked function
        # Remove the module if it's already loaded
        if "mcp_nixos.server" in sys.modules:
            del sys.modules["mcp_nixos.server"]

        # Now import the module, which will use our mocked function
        import mcp_nixos.server  # noqa: F401

        # Verify we got a fallback configuration
        assert hasattr(mcp_nixos.server, "cache_config")
        assert mcp_nixos.server.cache_config["initialized"] is False
        assert "error" in mcp_nixos.server.cache_config
        assert "Permission denied" in mcp_nixos.server.cache_config["error"]

        # Verify the server still initialized the contexts
        assert mcp_nixos.server.nixos_context is not None
        assert mcp_nixos.server.home_manager_context is not None
        assert mcp_nixos.server.darwin_context is not None

        # Try entering the lifespan to make sure it works
        mock_server = MagicMock()
        async with mcp_nixos.server.app_lifespan(mock_server) as context:
            # Verify we got our context
            assert "nixos_context" in context
            assert "home_manager_context" in context
            assert "darwin_context" in context
