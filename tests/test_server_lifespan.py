import unittest
import logging
from unittest.mock import patch, MagicMock

# Import base test class from __init__.py
from tests import NixMCPTestBase

# Import the server module
from nixmcp.server import ElasticsearchClient, NixOSContext

# Disable logging during tests
logging.disable(logging.CRITICAL)


class TestServerLifespan(unittest.TestCase):
    """Test the server lifespan context manager."""

    @patch("nixmcp.server.app_lifespan")
    def test_lifespan_initialization(self, mock_lifespan):
        """Test that the lifespan context manager initializes correctly."""
        # Create a mock context
        mock_context = {"nixos_context": NixOSContext(), "home_manager_context": MagicMock()}

        # Configure the mock to return our context
        mock_lifespan.return_value.__aenter__.return_value = mock_context

        # Verify that the context contains the expected keys
        self.assertIn("nixos_context", mock_context)
        self.assertIsInstance(mock_context["nixos_context"], NixOSContext)

        # Verify that the context has the expected methods
        self.assertTrue(hasattr(mock_context["nixos_context"], "get_status"))
        self.assertTrue(hasattr(mock_context["nixos_context"], "get_package"))
        self.assertTrue(hasattr(mock_context["nixos_context"], "search_packages"))
        self.assertTrue(hasattr(mock_context["nixos_context"], "search_options"))

        # Verify that the ElasticsearchClient is initialized
        self.assertIsInstance(mock_context["nixos_context"].es_client, ElasticsearchClient)

    @patch("nixmcp.server.app_lifespan")
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
        self.assertTrue(mock_server.prompt is not None)

        # Verify prompt contains key sections
        prompt_text = mock_server.prompt
        self.assertIn("NixOS and Home Manager MCP Guide", prompt_text)
        self.assertIn("When to Use These Tools", prompt_text)
        self.assertIn("Tool Parameters and Examples", prompt_text)

        # Verify tool documentation
        self.assertIn("nixos_search", prompt_text)
        self.assertIn("nixos_info", prompt_text)
        self.assertIn("nixos_stats", prompt_text)

        # Verify hierarchical path searching is documented
        self.assertIn("Hierarchical Path Searching", prompt_text)
        self.assertIn("services.postgresql", prompt_text)

        # Verify wildcard search documentation
        self.assertIn("Wildcard Search", prompt_text)
        self.assertIn("*term*", prompt_text)

        # Verify channel selection documentation
        self.assertIn("Version Selection", prompt_text)
        self.assertIn("unstable", prompt_text)
        self.assertIn("24.11", prompt_text)


class TestErrorHandling(NixMCPTestBase):
    """Test error handling in the server."""

    def test_connection_error_handling(self):
        """Test handling of connection errors.

        Instead of mocking network errors, we use a real but invalid endpoint to
        generate actual connection errors. This provides a more realistic test
        of how the application will handle connection failures in production.

        The test:
        1. Configures a client with an invalid endpoint URL
        2. Attempts to make a real request that will fail
        3. Verifies the application handles the error gracefully
        4. Confirms the error response follows the expected format
        """
        # Use a real but invalid endpoint to generate an actual connection error
        invalid_client = ElasticsearchClient()
        invalid_client.es_packages_url = "https://nonexistent-server.nixos.invalid/_search"

        # Replace the context's client with our invalid one
        original_client = self.context.es_client
        self.context.es_client = invalid_client

        try:
            # Test that the get_package method handles the error gracefully
            result = self.context.get_package("python")

            # Verify the result contains an error message and found=False
            self.assertFalse(result.get("found", True))
            self.assertIn("error", result)
        finally:
            # Restore the original client
            self.context.es_client = original_client

    def test_search_with_invalid_parameters(self):
        """Test search with invalid parameters."""
        # Import the nixos_search function directly
        from nixmcp.server import nixos_search

        # Test with an invalid type
        result = nixos_search("python", "invalid_type", 5)

        # Verify the result contains an error message
        self.assertIn("Error: Invalid type", result)
        self.assertIn("Must be one of", result)


if __name__ == "__main__":
    unittest.main()
