"""
NixMCP Server - A MCP server for NixOS resources.

This implements a comprehensive FastMCP server that provides MCP resources and tools
for querying NixOS packages and options using the Model Context Protocol (MCP).
The server communicates via standard input/output streams using a JSON-based
message format, allowing seamless integration with MCP-compatible AI models.

This server connects to the NixOS ElasticSearch API to provide information about:
- NixOS packages (name, version, description, programs)
- NixOS options (configuration options for the system)
- NixOS service configuration (like services.postgresql.*)

Elasticsearch Implementation Notes:
-----------------------------------
The server connects to the NixOS search Elasticsearch API with these details:
  - URL: https://search.nixos.org/backend/{index}/_search
  - Credentials: Basic authentication (public credentials from NixOS search)
  - Index pattern: latest-42-nixos-{channel} (e.g., latest-42-nixos-unstable)
  - Both packages and options are in the same index, distinguished by a "type" field
  - Hierarchical paths use a special query format with wildcards

Based on the official NixOS search implementation.
"""

from contextlib import asynccontextmanager
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Import our custom modules
from nixmcp.logging import setup_logging
from nixmcp.contexts.nixos_context import NixOSContext
from nixmcp.contexts.home_manager_context import HomeManagerContext
from nixmcp.resources.nixos_resources import register_nixos_resources
from nixmcp.resources.home_manager_resources import register_home_manager_resources
from nixmcp.tools.nixos_tools import register_nixos_tools
from nixmcp.tools.home_manager_tools import register_home_manager_tools

# Compatibility imports for tests - these are used by tests
# but unused in the actual server code (suppressed from linting)
from nixmcp.clients.elasticsearch_client import ElasticsearchClient  # noqa: F401
from nixmcp.clients.home_manager_client import HomeManagerClient  # noqa: F401
from nixmcp.cache.simple_cache import SimpleCache  # noqa: F401
from nixmcp.utils.helpers import create_wildcard_query  # noqa: F401
from nixmcp.tools.nixos_tools import nixos_search, nixos_info, nixos_stats  # noqa: F401
from nixmcp.tools.home_manager_tools import home_manager_search, home_manager_info, home_manager_stats  # noqa: F401
from nixmcp.resources.nixos_resources import (  # noqa: F401
    nixos_status_resource,
    package_resource,
    search_packages_resource,
    search_options_resource,
    option_resource,
    search_programs_resource,
    package_stats_resource,
)
from nixmcp.resources.home_manager_resources import (  # noqa: F401
    home_manager_status_resource,
    home_manager_search_options_resource,
    home_manager_option_resource,
    home_manager_stats_resource,
)

# Load environment variables from .env file
load_dotenv()

# Initialize logging
logger = setup_logging()

# Initialize the model contexts
nixos_context = NixOSContext()
home_manager_context = HomeManagerContext()


# Define the lifespan context manager for app initialization
@asynccontextmanager
async def app_lifespan(mcp_server: FastMCP):
    logger.info("Initializing NixMCP server")

    # Add prompt to guide assistants on using the MCP tools
    mcp_server.prompt = """
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

    ### For questions about...

    - **System-wide package availability**: Use `nixos_search(type="packages")`
    - **NixOS system configuration**: Use `nixos_search(type="options")`
    - **Executable programs**: Use `nixos_search(type="programs")`
    - **Home Manager configuration**: Use `home_manager_search()`
    - **User environment setup**: Use `home_manager_search()`
    - **Configuration for specific applications**:
      - Try `home_manager_search(query="programs.NAME")` first
      - If not found, try `nixos_search(query="NAME", type="packages")`

    ## When to Use These Tools

    - `nixos_search`: Use when you need to find NixOS packages, system options, or executable programs
        - For packages: Finding software available in NixOS by name, function, or description
        - For options: Finding system configuration options, especially service configurations
        - For programs: Finding which packages provide specific executable programs

    - `nixos_info`: Use when you need detailed information about a specific package or option
        - For packages: Getting version, description, homepage, license, provided executables
        - For options: Getting detailed descriptions, type information, default values, examples
        - Especially useful for service configuration options with related options and examples

    - `nixos_stats`: Use when you need statistics about NixOS packages
        - Distribution by channel, license, platforms
        - Overview of the NixOS package ecosystem

    - `home_manager_search`: Use when you need to find Home Manager configuration options
        - Finding options for configuring user environments with Home Manager
        - Getting details about the structure and usage of Home Manager options
        - Especially useful for program configurations like programs.git, programs.firefox, etc.
        - Use for user-specific configuration rather than system-wide settings

    - `home_manager_info`: Use when you need detailed information about a specific Home Manager option
        - Getting detailed descriptions, type information, default values, examples
        - Understanding the purpose and usage of Home Manager configuration options
        - Includes configuration examples for Home Manager options

    - `home_manager_stats`: Use when you need statistics about Home Manager options
        - Count of available options by category and type
        - Overview of the Home Manager configuration ecosystem

    ## Tool Parameters and Examples

    ### NixOS Tools

    #### nixos_search

    ```python
    nixos_search(
        query: str,              # Required: Search term like "firefox" or "services.postgresql"
        type: str = "packages",  # Optional: "packages", "options", or "programs"
        limit: int = 20,         # Optional: Max number of results
        channel: str = "unstable" # Optional: NixOS channel - "unstable" or "24.11"
    ) -> str
    ```

    Examples:
    - `nixos_search(query="python", type="packages")` - Find Python packages in the unstable channel
    - `nixos_search(query="services.postgresql", type="options")` - Find PostgreSQL service options
    - `nixos_search(query="firefox", type="programs", channel="24.11")` - Find packages with firefox executables
    - `nixos_search(query="services.nginx.virtualHosts", type="options")` - Find nginx virtual host options

    #### nixos_info

    ```python
    nixos_info(
        name: str,               # Required: Name of package or option
        type: str = "package",   # Optional: "package" or "option"
        channel: str = "unstable" # Optional: NixOS channel - "unstable" or "24.11"
    ) -> str
    ```

    Examples:
    - `nixos_info(name="firefox", type="package")` - Get detailed info about the firefox package
    - `nixos_info(name="services.postgresql.enable", type="option")` - Get details about the PostgreSQL enable option
    - `nixos_info(name="git", type="package", channel="24.11")` - Get package info from the 24.11 channel

    #### nixos_stats

    ```python
    nixos_stats() -> str
    ```

    Example:
    - `nixos_stats()` - Get statistics about NixOS packages

    ### Home Manager Tools

    #### home_manager_search

    ```python
    home_manager_search(
        query: str,              # Required: Search term like "programs.git" or "browsers"
        limit: int = 20          # Optional: Max number of results
    ) -> str
    ```

    Examples:
    - `home_manager_search(query="git")` - Find Home Manager options related to git
    - `home_manager_search(query="programs.alacritty")` - Find Alacritty terminal options
    - `home_manager_search(query="firefox")` - Find Firefox browser configuration options

    #### home_manager_info

    ```python
    home_manager_info(
        name: str                # Required: Name of the Home Manager option
    ) -> str
    ```

    Examples:
    - `home_manager_info(name="programs.git.enable")` - Get details about the Git enable option
    - `home_manager_info(name="programs.vscode")` - Get details about VSCode configuration

    #### home_manager_stats

    ```python
    home_manager_stats() -> str
    ```

    Example:
    - `home_manager_stats()` - Get statistics about Home Manager options

    ## Advanced Usage Tips

    ### Common Scenarios and Tool Selection

    #### Setting up a system service
    For configuring a system service like PostgreSQL in NixOS:
    1. `nixos_search(query="services.postgresql", type="options")` - Find available system service options
    2. `nixos_info(name="services.postgresql.enable", type="option")` - Get details about enabling the service

    #### Configuring a user application
    For configuring a user application like Git in Home Manager:
    1. `home_manager_search(query="programs.git")` - Find all Git configuration options
    2. `home_manager_info(name="programs.git.userName")` - Get details about specific options

    #### Finding a package
    1. `nixos_search(query="firefox", type="packages")` - Find Firefox package in NixOS

    #### Configuring a browser
    1. `home_manager_search(query="programs.firefox")` - Find Firefox configuration options in Home Manager

    #### Setting up shell configuration
    1. `home_manager_search(query="programs.bash")` or `home_manager_search(query="programs.zsh")`

    ### Hierarchical Path Searching

    Both NixOS and Home Manager tools have special handling for hierarchical option paths:

    - Direct paths like `services.postgresql` or `programs.git` automatically use enhanced queries
    - Wildcards are automatically added to hierarchical paths as needed
    - The system provides suggestions for common options when a service/program is found
    - Both systems provide related options and configuration examples

    ### Wildcard Search

    - Wildcards (`*`) are automatically added to most queries
    - For more specific searches, use explicit wildcards:
        - `*term*` - Contains the term anywhere
        - `term*` - Starts with the term
        - `*term` - Ends with the term

    ### Version Selection (NixOS only)

    - Use the `channel` parameter to specify which NixOS version to search:
        - `unstable` (default): Latest development branch with newest packages
        - `24.11`: Latest stable release with more stable packages

    ### Comparing NixOS vs Home Manager Configuration

    - **NixOS** (`/etc/nixos/configuration.nix`): Configures system-wide settings, services, and packages
    - **Home Manager** (`~/.config/nixpkgs/home.nix`): Configures user-specific settings, applications, and dotfiles

    #### Example: PostgreSQL
    - NixOS: `services.postgresql.*` - System-wide database service
    - Home Manager: Client configuration and tools related to PostgreSQL

    #### Example: Git
    - NixOS: System-wide Git package installation
    - Home Manager: `programs.git.*` - User config including gitconfig, identity, ignores

    #### Example: Firefox
    - NixOS: System-wide Firefox installation
    - Home Manager: `programs.firefox.*` - User profiles, extensions, settings
    """

    try:
        # We yield our contexts that will be accessible in all handlers
        yield {"nixos_context": nixos_context, "home_manager_context": home_manager_context}
    except Exception as e:
        logger.error(f"Error in server lifespan: {e}")
        raise
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down NixMCP server")
        # Close any open connections or resources
        try:
            # Add any cleanup code here if needed
            pass
        except Exception as e:
            logger.error(f"Error during server shutdown cleanup: {e}")


# Create the MCP server with the lifespan handler
logger.info("Creating FastMCP server instance")
mcp = FastMCP(
    "NixMCP",
    version="0.1.2",
    description="NixOS HTTP-based Model Context Protocol Server",
    lifespan=app_lifespan,
)


# Helper functions for context access
def get_nixos_context():
    return nixos_context


def get_home_manager_context():
    return home_manager_context


# Register all resources and tools
register_nixos_resources(mcp, get_nixos_context)
register_home_manager_resources(mcp, get_home_manager_context)
register_nixos_tools(mcp)
register_home_manager_tools(mcp)


if __name__ == "__main__":
    # This will start the server and keep it running
    try:
        logger.info("Starting NixMCP server...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running server: {e}", exc_info=True)
