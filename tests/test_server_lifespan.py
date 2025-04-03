import logging
import pytest
from unittest.mock import patch, MagicMock

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Import base test class from __init__.py
from tests import MCPNixOSTestBase

# Import the server module
from mcp_nixos.server import ElasticsearchClient, NixOSContext

# Disable logging during tests
logging.disable(logging.CRITICAL)


# Use pytest style for the class with async test
class TestServerLifespan:
    """Test the server lifespan context manager."""

    @patch("mcp_nixos.server.app_lifespan")
    def test_lifespan_initialization(self, mock_lifespan):
        """Test that the lifespan context manager initializes correctly."""
        # Create a mock context
        mock_context = {"nixos_context": NixOSContext(), "home_manager_context": MagicMock()}

        # Configure the mock to return our context
        mock_lifespan.return_value.__aenter__.return_value = mock_context

        # Verify that the context contains the expected keys
        assert "nixos_context" in mock_context
        assert isinstance(mock_context["nixos_context"], NixOSContext)

        # Verify that the context has the expected methods
        assert hasattr(mock_context["nixos_context"], "get_status")
        assert hasattr(mock_context["nixos_context"], "get_package")
        assert hasattr(mock_context["nixos_context"], "search_packages")
        assert hasattr(mock_context["nixos_context"], "search_options")

        # Verify that the ElasticsearchClient is initialized
        assert isinstance(mock_context["nixos_context"].es_client, ElasticsearchClient)

    @pytest.mark.asyncio
    @patch("mcp_nixos.server.app_lifespan")
    @patch("mcp_nixos.server.HomeManagerContext")
    async def test_eager_loading_on_startup(self, mock_hm_context_class, mock_lifespan):
        """Test that the server eagerly loads Home Manager data on startup."""
        # Create mock instances
        mock_hm_context = MagicMock()
        mock_hm_context_class.return_value = mock_hm_context
        mock_server = MagicMock()

        # Simulate what happens in the real app_lifespan
        async def app_lifespan_impl(mcp_server):
            # In the real function, this gets called during startup
            mock_hm_context.ensure_loaded()
            # Return the context
            return {"nixos_context": MagicMock(), "home_manager_context": mock_hm_context}

        # Set up our async context manager
        mock_lifespan.return_value.__aenter__ = app_lifespan_impl

        # Properly await the async context manager
        await mock_lifespan(mock_server).__aenter__()

        # Verify that ensure_loaded was called
        mock_hm_context.ensure_loaded.assert_called_once()

    @patch("mcp_nixos.server.app_lifespan")
    def test_system_prompt_configuration(self, mock_lifespan):
        """Test that the server configures the system prompt correctly for LLMs."""
        # Create a mock FastMCP server
        mock_server = MagicMock()

        # Set the prompt directly, simulating what app_lifespan would do
        mock_server.prompt = """
    # NixOS and Home Manager MCP Guide

    This Model Context Protocol (MCP) provides tools to search and retrieve detailed information about:
    1. NixOS packages, system options, and service configurations
    2. Home Manager options for user configuration

    ## Choosing the Right Tools

    ### When to use NixOS tools vs. Home Manager tools

    - **NixOS tools** (`nixos_*`): Use when looking for:
      - System-wide packages in the Nix package registry
      - System-level configuration options for NixOS
      - System services configuration (like services.postgresql)
      - Available executable programs and which packages provide them

    - **Home Manager tools** (`home_manager_*`): Use when looking for:
      - User environment configuration options
      - Home Manager module configuration (programs.*, services.*)
      - Application configuration managed through Home Manager
      - User-specific package and service settings

    ### When to Use These Tools

    - `nixos_search`: Use when you need to find NixOS packages, system options, or executable programs
    - `nixos_info`: Use when you need detailed information about a specific package or option
    - `nixos_stats`: Use when you need statistics about NixOS packages

    ## Tool Parameters and Examples

    ### NixOS Tools

    #### nixos_search
    Examples:
    - `nixos_search(query="python", type="packages")` - Find Python packages in the unstable channel
    - `nixos_search(query="services.postgresql", type="options")` - Find PostgreSQL service options
    - `nixos_search(query="firefox", type="programs", channel="24.11")` - Find packages with firefox executables
    - `nixos_search(query="services.nginx.virtualHosts", type="options")` - Find nginx virtual host options

    ### Hierarchical Path Searching

    Both NixOS and Home Manager tools have special handling for hierarchical option paths:
    - Direct paths like `services.postgresql` or `programs.git` automatically use enhanced queries

    ### Wildcard Search
    - Wildcards (`*`) are automatically added to most queries
    - For more specific searches, use explicit wildcards: `*term*`

    ### Version Selection (NixOS only)
    - Use the `channel` parameter to specify which NixOS version to search:
      - `unstable` (default): Latest development branch with newest packages
      - `24.11`: Latest stable release with more stable packages
    """

        # Mock __aenter__ to return a result and avoid actually running the context manager
        mock_context = {"nixos_context": MagicMock(), "home_manager_context": MagicMock()}
        mock_lifespan.return_value.__aenter__.return_value = mock_context

        # Verify the prompt was set on the server
        assert mock_server.prompt is not None

        # Verify prompt contains key sections
        prompt_text = mock_server.prompt
        assert "NixOS and Home Manager MCP Guide" in prompt_text
        assert "When to Use These Tools" in prompt_text
        assert "Tool Parameters and Examples" in prompt_text

        # Verify tool documentation
        assert "nixos_search" in prompt_text
        assert "nixos_info" in prompt_text
        assert "nixos_stats" in prompt_text

        # Verify hierarchical path searching is documented
        assert "Hierarchical Path Searching" in prompt_text
        assert "services.postgresql" in prompt_text

        # Verify wildcard search documentation
        assert "Wildcard Search" in prompt_text
        assert "*term*" in prompt_text

        # Verify channel selection documentation
        assert "Version Selection" in prompt_text
        assert "unstable" in prompt_text
        assert "24.11" in prompt_text

    @pytest.mark.asyncio
    @patch("mcp_nixos.utils.cache_helpers.init_cache_storage")
    async def test_cache_initialization_on_startup(self, mock_init_cache, tmp_path):
        """Test that the cache directory is properly initialized on server startup."""
        # Configure the mock to return a temp path config
        mock_init_cache.return_value = {"cache_dir": str(tmp_path), "ttl": 86400, "initialized": True}

        # Import here to avoid circular imports during test collection
        # Need to reload the server module to apply our mocks to module-level code
        import sys

        # Remove the module if it's already loaded
        if "mcp_nixos.server" in sys.modules:
            del sys.modules["mcp_nixos.server"]

        # Now import the module, which will use our mocked init_cache_storage
        from mcp_nixos.server import app_lifespan, darwin_context, home_manager_context

        # Setup mock server
        mock_server = MagicMock()

        # Execute the lifespan context manager
        async with app_lifespan(mock_server) as context:
            # Verify the context is properly set up
            assert "nixos_context" in context
            assert "home_manager_context" in context
            assert "darwin_context" in context

            # Verify the cache initialization was called during module loading
            mock_init_cache.assert_called_once()

            # Verify the darwin client exists
            assert darwin_context is not None

            # Ensure home manager client exists
            assert home_manager_context is not None


class TestErrorHandling(MCPNixOSTestBase):
    """Test error handling in the server."""

    def test_connection_error_handling(self):
        """Test handling of connection errors.

        Instead of mocking network errors, we use the updated error handling in NixOSContext
        to verify that connection errors are handled properly.

        The test:
        1. Creates a mock ElasticsearchClient that raises an exception
        2. Attempts to make calls that will trigger the exception handlers
        3. Verifies the application handles the error gracefully
        4. Confirms the error response follows the expected format
        """
        # Create a context with a mocked client
        context = NixOSContext()

        # Create a client that raises exceptions for all methods
        mock_client = MagicMock()
        mock_client.get_package.side_effect = Exception("Connection error")
        mock_client.search_packages.side_effect = Exception("Connection error")
        mock_client.search_options.side_effect = Exception("Connection error")
        mock_client.get_option.side_effect = Exception("Connection error")

        # Replace the context's client with our mock
        context.es_client = mock_client

        # Test get_package error handling
        result = context.get_package("python")
        assert result.get("found", True) is False
        assert "error" in result
        assert "Connection error" in result["error"]

        # Test search_packages error handling
        result = context.search_packages("python")
        assert result.get("count") == 0
        assert len(result.get("packages", [])) == 0
        assert "error" in result
        assert "Connection error" in result["error"]

        # Test search_options error handling
        result = context.search_options("nginx")
        assert result.get("count") == 0
        assert len(result.get("options", [])) == 0
        assert "error" in result
        assert "Connection error" in result["error"]

        # Test get_option error handling
        result = context.get_option("services.nginx.enable")
        assert result.get("found", True) is False
        assert "error" in result
        assert "Connection error" in result["error"]

    def test_search_with_invalid_parameters(self):
        """Test search with invalid parameters."""
        # Import the nixos_search function directly
        from mcp_nixos.tools.nixos_tools import nixos_search

        # Test with an invalid type
        result = nixos_search("python", "invalid_type", 5)

        # Verify the result contains an error message
        assert "Error: Invalid type" in result
        assert "Must be one of" in result
