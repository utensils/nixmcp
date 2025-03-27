"""
NixMCP Server - A MCP server for NixOS, Home Manager, and nix-darwin resources.

This implements a comprehensive FastMCP server that provides MCP resources and tools
for querying NixOS packages and options, Home Manager configuration options, and
nix-darwin macOS configuration options using the Model Context Protocol (MCP).
The server communicates via standard input/output streams using a JSON-based
message format, allowing seamless integration with MCP-compatible AI models.

This server provides information about:
- NixOS packages (name, version, description, programs) via Elasticsearch API
- NixOS options (configuration options for the system) via Elasticsearch API
- NixOS service configuration (like services.postgresql.*) via Elasticsearch API
- Home Manager options (user configuration options) via HTML documentation parsing
- nix-darwin options (macOS configuration options) via HTML documentation parsing

Elasticsearch Implementation Notes (NixOS):
-----------------------------------
The server connects to the NixOS search Elasticsearch API with these details:
  - URL: https://search.nixos.org/backend/{index}/_search
  - Credentials: Basic authentication (public credentials from NixOS search)
  - Index pattern: latest-42-nixos-{channel} (e.g., latest-42-nixos-unstable)
  - Both packages and options are in the same index, distinguished by a "type" field
  - Hierarchical paths use a special query format with wildcards

HTML Documentation Parsing (Home Manager and nix-darwin):
-----------------------------------
The server fetches and parses HTML documentation for Home Manager and nix-darwin:
  - Home Manager: Documentation from nix-community.github.io/home-manager/
  - nix-darwin: Documentation from daiderd.com/nix-darwin/manual/

Based on the official NixOS search implementation with additional parsing for
Home Manager and nix-darwin documentation.
"""

from contextlib import asynccontextmanager
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Import our custom modules
from nixmcp.logging import setup_logging
from nixmcp.contexts.nixos_context import NixOSContext
from nixmcp.contexts.home_manager_context import HomeManagerContext
from nixmcp.contexts.darwin.darwin_context import DarwinContext
from nixmcp.resources.nixos_resources import register_nixos_resources
from nixmcp.resources.home_manager_resources import register_home_manager_resources
from nixmcp.resources.darwin.darwin_resources import register_darwin_resources
from nixmcp.tools.nixos_tools import register_nixos_tools
from nixmcp.tools.home_manager_tools import register_home_manager_tools
from nixmcp.tools.darwin.darwin_tools import register_darwin_tools

# Compatibility imports for tests - these are used by tests
# but unused in the actual server code (suppressed from linting)
from nixmcp.clients.elasticsearch_client import ElasticsearchClient  # noqa: F401
from nixmcp.clients.home_manager_client import HomeManagerClient  # noqa: F401
from nixmcp.clients.darwin.darwin_client import DarwinClient  # noqa: F401
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
from nixmcp.resources.darwin.darwin_resources import (  # noqa: F401
    get_darwin_status,
    search_darwin_options,
    get_darwin_option,
    get_darwin_statistics,
)

# Load environment variables from .env file
load_dotenv()

# Import version to add to first log message
from nixmcp import __version__

# Initialize logging
logger = setup_logging()
logger.info(f"Starting NixMCP v{__version__}")

# Initialize the model contexts
nixos_context = NixOSContext()
home_manager_context = HomeManagerContext()
darwin_context = DarwinContext()


# Define the lifespan context manager for app initialization
@asynccontextmanager
async def app_lifespan(mcp_server: FastMCP):
    logger.info("Initializing NixMCP server components")

    # Start loading Home Manager data in background thread
    # This way the server can start up immediately without blocking
    logger.info("Starting background loading of Home Manager data...")

    # Trigger the background loading process
    home_manager_context.hm_client.load_in_background()

    # Start loading Darwin data in the background
    logger.info("Starting background loading of Darwin data...")

    # Start the Darwin context
    try:
        await darwin_context.startup()
        logger.info(f"Darwin context status: {darwin_context.status}")
    except Exception as e:
        logger.error(f"Error starting Darwin context: {e}")

    # Don't wait for the data to be fully loaded
    logger.info("Server will continue startup while Home Manager and Darwin data loads in background")

    # Add prompt to guide assistants on using the MCP tools
    mcp_server.prompt = """
    # NixOS, Home Manager, and nix-darwin MCP Guide

    This Model Context Protocol (MCP) provides tools to search and retrieve detailed information about:
    1. NixOS packages, system options, and service configurations
    2. Home Manager options for user configuration
    3. nix-darwin options for macOS configuration

    ## Choosing the Right Tools

    ### When to use NixOS, Home Manager, or nix-darwin tools

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

    - **nix-darwin tools** (`darwin_*`): Use when looking for:
      - macOS-specific configuration options
      - nix-darwin module configuration (services.*, system.*)
      - macOS-specific service configurations (launchd, etc.)
      - macOS system and environment settings

    ### For questions about...

    - **System-wide package availability**: Use `nixos_search(type="packages")`
    - **NixOS system configuration**: Use `nixos_search(type="options")`
    - **Executable programs**: Use `nixos_search(type="programs")`
    - **Home Manager configuration**: Use `home_manager_search()`
    - **User environment setup**: Use `home_manager_search()`
    - **macOS configuration**: Use `darwin_search()`
    - **nix-darwin system settings**: Use `darwin_search(query="system")`
    - **macOS services**: Use `darwin_search(query="services")`
    - **Configuration for specific applications**:
      - Try `home_manager_search(query="programs.NAME")` first
      - If not found, try `nixos_search(query="NAME", type="packages")`
      - For macOS-specific apps, try `darwin_search(query="programs.NAME")`

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

    - `darwin_search`: Use when you need to find nix-darwin configuration options
        - Finding macOS-specific configuration options
        - Getting details about nix-darwin module options
        - Especially useful for macOS service configurations

    - `darwin_info`: Use when you need detailed information about a specific nix-darwin option
        - Getting detailed descriptions, type information, default values, examples
        - Understanding how to configure macOS-specific features
        - Includes examples for nix-darwin configurations

    - `darwin_stats`: Use when you need statistics about nix-darwin options
        - Count of available options by category
        - Overview of the nix-darwin configuration ecosystem

    - `darwin_list_options`: Use when you need to list all top-level nix-darwin option categories
        - Get a categorized view of all available option areas
        - Find the right category for specific macOS configurations

    - `darwin_options_by_prefix`: Use when you need to see all options in a specific category
        - List all options under a specific prefix (e.g., services, system, etc.)
        - Get a comprehensive view of related configuration options

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
    nixos_stats(
        channel: str = "unstable" # Optional: NixOS channel - "unstable" or "24.11"
    ) -> str
    ```

    Examples:
    - `nixos_stats()` - Get statistics about NixOS packages and options in the unstable channel
    - `nixos_stats(channel="stable")` - Get statistics for the stable channel

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

    ### nix-darwin Tools

    #### darwin_search

    ```python
    darwin_search(
        query: str,              # Required: Search term like "services.yabai" or "system"
        limit: int = 20          # Optional: Max number of results
    ) -> str
    ```

    Examples:
    - `darwin_search(query="yabai")` - Find nix-darwin options related to yabai
    - `darwin_search(query="system.keyboard")` - Find keyboard-related system options
    - `darwin_search(query="services")` - Find all available service configurations

    #### darwin_info

    ```python
    darwin_info(
        name: str                # Required: Name of the nix-darwin option
    ) -> str
    ```

    Examples:
    - `darwin_info(name="services.yabai.enable")` - Get details about enabling the yabai service
    - `darwin_info(name="system.defaults.dock")` - Get details about dock configuration

    #### darwin_stats

    ```python
    darwin_stats() -> str
    ```

    Example:
    - `darwin_stats()` - Get statistics about nix-darwin options

    #### darwin_list_options

    ```python
    darwin_list_options() -> str
    ```

    Example:
    - `darwin_list_options()` - List all top-level nix-darwin option categories

    #### darwin_options_by_prefix

    ```python
    darwin_options_by_prefix(
        option_prefix: str       # Required: The option prefix path (e.g., "services", "system.defaults")
    ) -> str
    ```

    Examples:
    - `darwin_options_by_prefix(option_prefix="services")` - List all service-related options
    - `darwin_options_by_prefix(option_prefix="system.defaults")` - List all system default options

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

    #### Configuring macOS dock behavior
    1. `darwin_search(query="system.defaults.dock")` - Find all dock-related options
    2. `darwin_info(name="system.defaults.dock.autohide")` - Get details about dock autohide

    #### Setting up a macOS window manager
    1. `darwin_search(query="services.yabai")` - Find all yabai-related options
    2. `darwin_info(name="services.yabai.enable")` - Get details about enabling yabai

    #### Configuring macOS keyboard settings
    1. `darwin_search(query="system.keyboard")` - Find keyboard-related options

    ### Hierarchical Path Searching

    All three systems (NixOS, Home Manager, and nix-darwin) have special handling for hierarchical option paths:

    - Direct paths like `services.postgresql`, `programs.git`, or `system.defaults.dock` use enhanced queries
    - Wildcards are automatically added to hierarchical paths as needed
    - The system provides suggestions for common options when a service/program is found
    - All systems provide related options and configuration examples

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

    ### Comparing NixOS vs Home Manager vs nix-darwin Configuration

    - **NixOS** (`/etc/nixos/configuration.nix`): Configures Linux system-wide settings, services, and packages
    - **Home Manager** (`~/.config/nixpkgs/home.nix`): Configures user-specific settings, applications, and dotfiles
    - **nix-darwin** (`~/.nixpkgs/darwin-configuration.nix`): Configures macOS system-wide settings and services

    #### Example: PostgreSQL
    - NixOS: `services.postgresql.*` - System-wide database service on Linux
    - Home Manager: Client configuration and tools related to PostgreSQL
    - nix-darwin: `services.postgresql.*` - System-wide database service on macOS

    #### Example: Git
    - NixOS: System-wide Git package installation
    - Home Manager: `programs.git.*` - User config including gitconfig, identity, ignores
    - nix-darwin: System-wide Git package installation on macOS

    #### Example: Firefox
    - NixOS: System-wide Firefox installation
    - Home Manager: `programs.firefox.*` - User profiles, extensions, settings
    - nix-darwin: System-wide Firefox installation on macOS

    #### Example: Window Management
    - NixOS: X11/Wayland configuration
    - Home Manager: User-specific window manager configuration
    - nix-darwin: `services.yabai.*` - macOS-specific window management
    """

    try:
        # We yield our contexts that will be accessible in all handlers
        yield {
            "nixos_context": nixos_context,
            "home_manager_context": home_manager_context,
            "darwin_context": darwin_context,
        }
    except Exception as e:
        logger.error(f"Error in server lifespan: {e}")
        raise
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down NixMCP server")
        # Close any open connections or resources
        try:
            # Shutdown Darwin context
            try:
                await darwin_context.shutdown()
                logger.debug("Darwin context shutdown complete")  # Changed to debug level
            except Exception as e:
                logger.error(f"Error shutting down Darwin context: {e}")

            # Add any other cleanup code here if needed
        except Exception as e:
            logger.error(f"Error during server shutdown cleanup: {e}")


# Create the MCP server with the lifespan handler
logger.info("Creating FastMCP server instance")
mcp = FastMCP(
    "NixMCP",
    version=__version__,
    description="NixOS Model Context Protocol Server",
    lifespan=app_lifespan,
    capabilities=["resources", "tools"],  # "completions" capability disabled until SDK implementation
)


# Helper functions for context access
def get_nixos_context():
    return nixos_context


def get_home_manager_context():
    return home_manager_context


def get_darwin_context():
    return darwin_context


# Import completion handler (temporarily disabled)
# from nixmcp.completions import handle_completion

# Register all resources and tools
register_nixos_resources(mcp, get_nixos_context)
register_home_manager_resources(mcp, get_home_manager_context)
register_darwin_resources(darwin_context, mcp)
register_nixos_tools(mcp)
register_home_manager_tools(mcp)
register_darwin_tools(darwin_context, mcp)

# No need to manually add tools here - will be handled by the register_darwin_tools function


# Completion support is temporarily disabled until the MCP SDK fully implements it
# The MCP spec includes "completion/complete" but it's not yet implemented in the SDK
# Below is the commented-out implementation that will be enabled once the MCP SDK supports it
"""
# Register completion method - the MCP protocol uses "completion/complete" for the method name
# but tool names in MCP must conform to the pattern ^[a-zA-Z0-9_-]{1,64}$, so we use underscores
# and the framework maps between them
@mcp.tool("completion_complete")
async def mcp_handle_completion(params: dict) -> dict:
    # Handle MCP completion requests.
    # This function is registered as "completion_complete" to match MCP naming conventions
    # while conforming to the restriction that tool names cannot contain slashes.
    logger.info("Received completion request")
    logger.debug(f"Raw completion params: {params}")

    try:
        # Pass the request to our completion handler
        result = await handle_completion(params, nixos_context, home_manager_context)
        # Log the completion results at DEBUG level
        logger.debug(f"Completion result: {result}")
        return result
    except Exception as e:
        # Log exceptions in completion handling
        logger.error(f"Error in completion handler: {e}", exc_info=True)
        return {"items": []}
"""


if __name__ == "__main__":
    # This will start the server and keep it running
    try:
        logger.info("Starting NixMCP server...")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running server: {e}", exc_info=True)
