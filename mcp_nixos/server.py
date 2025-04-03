"""
MCP-NixOS Server - A MCP server for NixOS, Home Manager, and nix-darwin resources.

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
  - nix-darwin: Documentation from nix-darwin.github.io/nix-darwin/manual/

Based on the official NixOS search implementation with additional parsing for
Home Manager and nix-darwin documentation.
"""

import asyncio
import os
import psutil
import signal
import sys
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from mcp_nixos.cache.simple_cache import SimpleCache  # noqa: F401
from mcp_nixos.clients.darwin.darwin_client import DarwinClient  # noqa: F401

# Compatibility imports for tests - these are used by tests
# but unused in the actual server code (suppressed from linting)
from mcp_nixos.clients.elasticsearch_client import ElasticsearchClient  # noqa: F401
from mcp_nixos.clients.home_manager_client import HomeManagerClient  # noqa: F401
from mcp_nixos.contexts.darwin.darwin_context import DarwinContext
from mcp_nixos.contexts.home_manager_context import HomeManagerContext
from mcp_nixos.contexts.nixos_context import NixOSContext

# Import our custom modules
from mcp_nixos.logging import setup_logging
from mcp_nixos.resources.darwin.darwin_resources import (  # noqa: F401
    get_darwin_option,
    get_darwin_statistics,
    get_darwin_status,
    register_darwin_resources,
    search_darwin_options,
)
from mcp_nixos.resources.home_manager_resources import (  # noqa: F401
    home_manager_option_resource,
    home_manager_search_options_resource,
    home_manager_stats_resource,
    home_manager_status_resource,
    register_home_manager_resources,
)
from mcp_nixos.resources.nixos_resources import (  # noqa: F401
    nixos_status_resource,
    option_resource,
    package_resource,
    package_stats_resource,
    register_nixos_resources,
    search_options_resource,
    search_packages_resource,
    search_programs_resource,
)
from mcp_nixos.tools.darwin.darwin_tools import register_darwin_tools
from mcp_nixos.tools.home_manager_tools import register_home_manager_tools
from mcp_nixos.tools.nixos_tools import register_nixos_tools
from mcp_nixos.utils.helpers import create_wildcard_query  # noqa: F401

# Load environment variables from .env file
load_dotenv()

# Import version to add to first log message
from mcp_nixos import __version__

# Initialize logging
logger = setup_logging()
logger.info(f"Starting MCP-NixOS v{__version__}")

# Ensure cache directory is properly initialized before any clients
from mcp_nixos.utils.cache_helpers import init_cache_storage

# Initialize the cache directory explicitly before creating clients
cache_config = init_cache_storage()
logger.info(
    f"Cache initialized with directory: {cache_config['cache_dir']} (initialized: {cache_config['initialized']})"
)
if not cache_config["initialized"]:
    logger.warning(f"Using fallback cache directory due to error: {cache_config.get('error', 'Unknown error')}")

# Initialize the model contexts
nixos_context = NixOSContext()
home_manager_context = HomeManagerContext()
darwin_context = DarwinContext()


# Define a helper function for handling async timeouts
async def async_with_timeout(coro_func, timeout_seconds=5.0, operation_name="operation"):
    """Execute a coroutine with a timeout.

    Args:
        coro_func: A function that returns a coroutine when called
        timeout_seconds: Maximum time to wait (seconds)
        operation_name: Name of the operation for logging purposes

    Returns:
        The result of the coroutine, or None if it timed out
    """
    try:
        # Get the coroutine at execution time, not when passed to the function
        coro = coro_func()
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning(f"{operation_name} timed out after {timeout_seconds}s")
        return None
    except Exception as e:
        logger.error(f"Error during {operation_name}: {e}")
        return None


async def run_precache_async():
    """Run all initialization and cache population, then exit.

    This function runs the same initialization steps as the server startup
    but waits for all caching operations to complete before returning.
    """
    logger.info("Starting pre-cache initialization")

    # Start loading Home Manager data
    logger.info("Loading Home Manager data...")
    home_manager_context.hm_client.load_in_background()

    # Start loading Darwin data
    logger.info("Loading Darwin data...")
    try:
        await async_with_timeout(
            lambda: darwin_context.startup(), timeout_seconds=30.0, operation_name="Darwin context startup"
        )
        logger.info(f"Darwin context status: {darwin_context.status}")
    except Exception as e:
        logger.error(f"Error starting Darwin context: {e}")

    # Wait for Home Manager client to complete loading
    # Use a polling approach since there's no explicit wait_for_loading method
    logger.info("Waiting for Home Manager data to complete loading...")
    max_wait_seconds = 120
    wait_interval = 2
    start_time = time.time()

    while time.time() - start_time < max_wait_seconds:
        with home_manager_context.hm_client.loading_lock:
            if hasattr(home_manager_context.hm_client, "is_loaded") and home_manager_context.hm_client.is_loaded:
                logger.info("Home Manager data finished loading")
                break
            if (
                hasattr(home_manager_context.hm_client, "loading_error")
                and home_manager_context.hm_client.loading_error
            ):
                logger.error(f"Home Manager loading failed: {home_manager_context.hm_client.loading_error}")
                break
        logger.debug(f"Home Manager data still loading, waiting {wait_interval}s...")
        await asyncio.sleep(wait_interval)
    else:
        logger.warning(f"Timed out after {max_wait_seconds}s waiting for Home Manager data to load")

    logger.info("All initialization completed successfully")
    return True


def run_precache():
    """Run all initialization and cache population synchronously, then exit."""
    try:
        return asyncio.run(run_precache_async())
    except KeyboardInterrupt:
        logger.info("Pre-cache operation interrupted")
        return False
    except Exception as e:
        logger.error(f"Error during pre-cache: {e}", exc_info=True)
        return False


# Define the lifespan context manager for app initialization
@asynccontextmanager
async def app_lifespan(mcp_server: FastMCP):
    logger.info("Initializing MCP-NixOS server components")

    # Import state persistence
    from mcp_nixos.utils.state_persistence import get_state_persistence

    # Create state tracking with initial value
    state_persistence = get_state_persistence()
    state_persistence.load_state()

    # Track connection count across reconnections
    connection_count = state_persistence.increment_counter("connection_count")
    logger.info(f"This is connection #{connection_count} since server installation")

    # Create synchronization for MCP protocol initialization
    protocol_initialized = asyncio.Event()
    app_ready = asyncio.Event()

    # Track initialization state in context
    lifespan_context = {
        "nixos_context": nixos_context,
        "home_manager_context": home_manager_context,
        "darwin_context": darwin_context,
        "is_ready": False,
        "initialization_time": time.time(),
        "connection_count": connection_count,
    }

    # Handle MCP protocol handshake
    # FastMCP doesn't expose a public API for modifying initialize behavior,
    # but it handles the initialize/initialized protocol automatically.
    # We'll use protocol_initialized.set() when we detect the first connection.

    # We'll mark the initialization as complete as soon as app is ready
    logger.info("Setting protocol initialization events")
    protocol_initialized.set()

    # This will trigger waiting for connection
    logger.info("App is ready for requests")
    lifespan_context["is_ready"] = True

    # Start loading Home Manager data in background thread
    # This way the server can start up immediately without blocking
    logger.info("Starting background loading of Home Manager data...")

    # Trigger the background loading process
    home_manager_context.hm_client.load_in_background()

    # Start loading Darwin data in the background
    logger.info("Starting background loading of Darwin data...")

    # Start the Darwin context with a timeout
    try:
        await async_with_timeout(
            lambda: darwin_context.startup(), timeout_seconds=10.0, operation_name="Darwin context startup"
        )
        logger.info(f"Darwin context status: {darwin_context.status}")
    except Exception as e:
        logger.error(f"Error starting Darwin context: {e}")

    # Don't wait for the data to be fully loaded
    logger.info("Server will continue startup while Home Manager and Darwin data loads in background")

    # Mark app as ready for requests
    logger.info("App is ready for requests, waiting for MCP protocol initialization")
    app_ready.set()

    # Wait for MCP protocol initialization (with timeout)
    try:
        await asyncio.wait_for(protocol_initialized.wait(), timeout=5.0)
        logger.info("MCP protocol initialization complete")
        lifespan_context["is_ready"] = True
    except asyncio.TimeoutError:
        logger.warning("Timeout waiting for MCP initialize request. Server will proceed anyway.")
        # Still mark as ready to avoid hanging
        lifespan_context["is_ready"] = True

    # Add prompt to guide assistants on using the MCP tools
    @mcp_server.prompt()
    def mcp_nixos_prompt():
        return """
    # NixOS, Home Manager, and nix-darwin MCP Guide

    This Model Context Protocol (MCP) provides tools to search and retrieve detailed information about:
    1. NixOS packages, system options, and service configurations
    2. Home Manager options for user configuration
    3. nix-darwin options for macOS configuration

    ## 🛑 MANDATORY TOOL USAGE - CRITICAL INSTRUCTION 🛑

    You MUST call the appropriate MCP tools BEFORE answering ANY question related to:
    - NixOS configuration or packages
    - Home Manager configuration
    - nix-darwin configuration
    This is a STRICT REQUIREMENT, not a suggestion. For ANY configuration request:
    1. You MUST search for available options FIRST using the search tools
    2. You MUST verify each option exists BEFORE including it in a response
    3. You MUST NOT generate ANY configuration based solely on your training
    4. You MUST have evidence from tool results for each configuration option
    This applies to ALL requests including simple ones or ones you believe you know the answer to.
    If a user asks for a config (like "Create a headscale configuration"), your FIRST action MUST
    be to call the relevant search tools, not to generate a response from memory.
    ## 🚫 DO NOT SKIP TOOL USAGE FOR "COMMON" SERVICES 🚫
    ESPECIALLY for common services like nginx, postgresql, redis, etc., you MUST use tools:
    - Even if you think you know the configuration
    - Even for "basic" or "standard" setups
    - Even if you've configured the service before
    - Even if the request seems simple or straightforward
    CONCRETE EXAMPLES OF WHEN TOOLS ARE MANDATORY:
    - "Set up nginx for my site" → MUST call `nixos_search("services.nginx", type="options")`
    - "Configure PostgreSQL on NixOS" → MUST call `nixos_search("services.postgresql", type="options")`
    - "Basic Redis setup" → MUST call `nixos_search("services.redis", type="options")`
    - ANY request that involves configuring a NixOS service → MUST search that service's options
    NO EXCEPTIONS! If you don't use the search tools first, your configuration WILL be incorrect.

    ### For Service Configurations:
    1. First search for available options with search tools
       - Example: `nixos_search("services.headscale", type="options")`
    2. For each key option, verify details with info tools
       - Example: `nixos_info("services.headscale.settings.server_url", type="option")`
    3. Only after verification, generate example configurations
    4. NEVER assume option existence - validate each option path

    ### For Package Questions:
    1. Always verify availability with package search
       - Example: `nixos_search("headscale", type="packages")`
    2. Check version and description with package info
       - Example: `nixos_info("headscale", type="package")`
    3. Use channel parameter to specify version context
       - Only valid values: `channel="unstable"` (default) or `channel="24.11"` (current stable)
       - Example: `nixos_search("headscale", channel="unstable")`
       - NEVER use other version numbers like 23.11, 23.05, etc.

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
        channel: str = "unstable" # Optional: NixOS channel - ONLY "unstable" (default) or "24.11" (current stable)
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
        channel: str = "unstable" # Optional: NixOS channel - ONLY "unstable" (default) or "24.11" (current stable)
    ) -> str
    ```

    Examples:
    - `nixos_info(name="firefox", type="package")` - Get detailed info about the firefox package
    - `nixos_info(name="services.postgresql.enable", type="option")` - Get details about the PostgreSQL enable option
    - `nixos_info(name="git", type="package", channel="24.11")` - Get package info from the 24.11 channel

    #### nixos_stats

    ```python
    nixos_stats(
        channel: str = "unstable" # Optional: NixOS channel - ONLY "unstable" (default) or "24.11" (current stable)
    ) -> str
    ```

    Examples:
    - `nixos_stats()` - Get statistics about NixOS packages and options in the unstable channel
    - `nixos_stats(channel="24.11")` - Get statistics for the current stable channel

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
    3. CRITICAL: For each option you plan to include in a configuration:
       - Verify the option exists with search tools
       - Check the option type and description with info tools
       - Only use options that actually exist in the documentation
       - Use exact option names as shown in the documentation
       - Provide appropriate default values based on documented examples

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
        - `24.11`: Current stable release (as of 2024) with more stable packages
    IMPORTANT: The current stable version is 24.11. DO NOT use outdated versions like 23.11, 23.05, 22.11, etc.
    Always use either "unstable" (default) or "24.11" as the channel parameter value.

    ### Comparing NixOS vs Home Manager vs nix-darwin Configuration

    IMPORTANT: Always verify option existence with appropriate search tools before using these paths!

    - **NixOS** (`/etc/nixos/configuration.nix`): Configures Linux system-wide settings, services, and packages
    - **Home Manager** (`~/.config/nixpkgs/home.nix`): Configures user-specific settings, applications, and dotfiles
    - **nix-darwin** (`~/.nixpkgs/darwin-configuration.nix`): Configures macOS system-wide settings and services

    #### Example: PostgreSQL
    Always verify with: `nixos_search("services.postgresql", type="options")` and `darwin_search("services.postgresql")`
    - NixOS: `services.postgresql.*` - System-wide database service on Linux
    - Home Manager: Client configuration and tools related to PostgreSQL
    - nix-darwin: `services.postgresql.*` - System-wide database service on macOS

    #### Example: Git
    Always verify with: `nixos_search("git", type="packages")` and `home_manager_search("programs.git")`
    - NixOS: System-wide Git package installation
    - Home Manager: `programs.git.*` - User config including gitconfig, identity, ignores
    - nix-darwin: System-wide Git package installation on macOS

    #### Example: Firefox
    Always verify with: `nixos_search("firefox", type="packages")` and `home_manager_search("programs.firefox")`
    - NixOS: System-wide Firefox installation
    - Home Manager: `programs.firefox.*` - User profiles, extensions, settings
    - nix-darwin: System-wide Firefox installation on macOS

    #### Example: Window Management
    Always verify with appropriate tools: `darwin_search("services.yabai")` for macOS
    - NixOS: X11/Wayland configuration
    - Home Manager: User-specific window manager configuration
    - nix-darwin: `services.yabai.*` - macOS-specific window management
    #### Example: Headscale (Tailscale Control Server)
    When asked about Headscale configuration, you MUST:
    1. First run: `nixos_search("headscale", type="packages")` to verify package availability
    2. Then run: `nixos_search("services.headscale", type="options")` to find ALL available options
    3. For key options, run: `nixos_info("services.headscale.enable", type="option")`
    4. Verify EVERY option you plan to include in configuration
    5. Only after verification, generate a configuration using ONLY verified options

    #### Example: Nginx Web Server
    When asked about Nginx configuration, you MUST:
    1. First run: `nixos_search("services.nginx", type="options")` to find ALL available options
    2. For SSL/TLS, run: `nixos_search("services.nginx.virtualHosts", type="options")`
    3. For specific settings, run: `nixos_info("services.nginx.virtualHosts", type="option")`
    4. Check SSL options with: `nixos_search("security.acme", type="options")`
    5. Verify EVERY option you include (enableACME, forceSSL, root, locations, etc.)
    6. Only after verification, generate a configuration using ONLY verified options
    REMEMBER: For all configurations, validate EACH option with the appropriate info tool before including it.
    If you cannot verify an option exists, DO NOT include it in your response.
    ## Automatic Tool Triggers - REQUIRED
    For these specific request patterns, you MUST IMMEDIATELY use the indicated tools:
    | When user asks for... | Your FIRST action MUST be... |
    |---|---|
    | "Create a [service] configuration" | `nixos_search("services.[service]", type="options")` |
    | "Create a [service] server" | `nixos_search("services.[service]", type="options")` |
    | "Configure [service] in NixOS" | `nixos_search("services.[service]", type="options")` |
    | "NixOS configuration for [service]" | `nixos_search("services.[service]", type="options")` |
    | "Set up [service] in NixOS" | `nixos_search("services.[service]", type="options")` |
    | "How to configure [service]" | `nixos_search("services.[service]", type="options")` |
    | "How to set up [service]" | `nixos_search("services.[service]", type="options")` |
    | "NixOS module for [service]" | `nixos_search("services.[service]", type="options")` |
    | "Basic [service] setup" | `nixos_search("services.[service]", type="options")` |
    | "Create a [service] for [domain/purpose]" | `nixos_search("services.[service]", type="options")` |
    | "Is [package] available?" | `nixos_search("[package]", type="packages")` |
    | "Home Manager config for [program]" | `home_manager_search("programs.[program]")` |
    | "Darwin configuration for [service]" | `darwin_search("services.[service]")` |
    These are not suggestions - they are REQUIRED first steps for ANY request matching these patterns.
    """

    try:
        # Save the final state before yielding control to server
        from mcp_nixos.utils.state_persistence import get_state_persistence

        state_persistence = get_state_persistence()
        state_persistence.set_state("last_startup_time", time.time())
        state_persistence.save_state()

        # We yield our contexts that will be accessible in all handlers
        yield lifespan_context
    except Exception as e:
        logger.error(f"Error in server lifespan: {e}")
        raise
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down MCP-NixOS server")

        # Track start time for overall shutdown duration
        shutdown_start = time.time()

        # Save final state before shutdown
        try:
            from mcp_nixos.utils.state_persistence import get_state_persistence

            state_persistence = get_state_persistence()
            state_persistence.set_state("last_shutdown_time", time.time())
            state_persistence.set_state("shutdown_reason", "normal")

            # Calculate uptime if we have an initialization time
            if lifespan_context.get("initialization_time"):
                uptime = time.time() - lifespan_context["initialization_time"]
                state_persistence.set_state("last_uptime", uptime)
                logger.info(f"Server uptime: {uptime:.2f}s")

            # Save state to disk
            state_persistence.save_state()
        except Exception as e:
            logger.error(f"Error saving state during shutdown: {e}")

        # Create coroutines for shutdown operations
        shutdown_coroutines = []

        # Add Darwin context shutdown with timeout
        if hasattr(darwin_context, "shutdown") and callable(darwin_context.shutdown):
            shutdown_coroutines.append(
                async_with_timeout(
                    lambda: darwin_context.shutdown(), timeout_seconds=0.5, operation_name="Darwin context shutdown"
                )
            )

        # Add shutdown for home_manager_context if a shutdown method is available
        if hasattr(home_manager_context, "shutdown") and callable(home_manager_context.shutdown):
            shutdown_coroutines.append(
                async_with_timeout(
                    lambda: home_manager_context.shutdown(),
                    timeout_seconds=0.5,
                    operation_name="Home Manager context shutdown",
                )
            )

        # Add shutdown for nixos_context if a shutdown method is available
        if hasattr(nixos_context, "shutdown") and callable(nixos_context.shutdown):
            shutdown_coroutines.append(
                async_with_timeout(
                    lambda: nixos_context.shutdown(), timeout_seconds=0.5, operation_name="NixOS context shutdown"
                )
            )

        # Execute all shutdown operations truly concurrently
        try:
            # Create individual tasks for each coroutine to ensure they run concurrently
            shutdown_tasks = [asyncio.create_task(coro) for coro in shutdown_coroutines]

            # Wait for all tasks to complete with an overall timeout
            await asyncio.wait_for(
                asyncio.gather(*shutdown_tasks, return_exceptions=True),
                timeout=0.8,  # Overall timeout for all shutdown operations
            )
            logger.debug("All context shutdowns completed")
        except asyncio.TimeoutError:
            logger.warning("Some shutdown operations timed out and were terminated")
            # Record abnormal shutdown in state
            try:
                state_persistence = get_state_persistence()
                state_persistence.set_state("shutdown_reason", "timeout")
                state_persistence.save_state()
            except Exception:
                pass  # Avoid cascading errors
        except Exception as e:
            logger.error(f"Error during concurrent shutdown operations: {e}")
            # Record error in state
            try:
                state_persistence = get_state_persistence()
                state_persistence.set_state("shutdown_reason", f"error: {str(e)}")
                state_persistence.save_state()
            except Exception:
                pass  # Avoid cascading errors

        # Log shutdown duration
        shutdown_duration = time.time() - shutdown_start
        logger.info(f"Shutdown completed in {shutdown_duration:.2f}s")


# Create the MCP server with the lifespan handler
logger.info("Creating FastMCP server instance")
mcp = FastMCP(
    "MCP-NixOS",
    version=__version__,
    description="NixOS Model Context Protocol Server",
    lifespan=app_lifespan,
    capabilities=["resources", "tools"],
)


# Helper functions for context access
def get_nixos_context():
    return nixos_context


def get_home_manager_context():
    return home_manager_context


def get_darwin_context():
    return darwin_context


# Register all resources and tools
register_nixos_resources(mcp, get_nixos_context)
register_home_manager_resources(mcp, get_home_manager_context)
register_darwin_resources(darwin_context, mcp)
register_nixos_tools(mcp)
register_home_manager_tools(mcp)
register_darwin_tools(darwin_context, mcp)

# No need to manually add tools here - will be handled by the register_darwin_tools function


# Signal handling is now managed by FastMCP framework via app_lifespan


if __name__ == "__main__":
    # This will start the server and keep it running
    try:
        # Log server initialization with additional environment info
        logger.info("Initializing MCP-NixOS server")

        # Log process and environment information for debugging
        try:
            process = psutil.Process()
            # Log basic process info
            logger.info(f"Process info - PID: {process.pid}, Parent PID: {process.ppid()}")

            # Try to get parent process info
            try:
                parent = psutil.Process(process.ppid())
                logger.info(f"Parent process: {parent.name()} (PID: {parent.pid})")
                parent_cmdline = " ".join(parent.cmdline())
                logger.debug(f"Parent command line: {parent_cmdline}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                logger.info("Unable to access parent process information")

            # Check if running under Windsurf or other MCP client
            windsurf_detected = False
            for env_var in os.environ:
                if "WINDSURF" in env_var.upper() or "WINDSURFER" in env_var.upper():
                    windsurf_detected = True
                    logger.info(f"Detected Windsurf environment: {env_var}={os.environ[env_var]}")

            if windsurf_detected:
                logger.info("Running under Windsurf - configuring for Windsurf compatibility")

                # Log available signals on this platform
                signal_names = []
                for sig_attr in dir(signal):
                    if sig_attr.startswith("SIG") and not sig_attr.startswith("SIG_"):
                        signal_names.append(sig_attr)
                logger.debug(f"Available signals on this platform: {', '.join(signal_names)}")

        except Exception as e:
            logger.error(f"Error getting process info during startup: {e}")

        logger.info("Starting MCP-NixOS server event loop")
        mcp.run()
    except KeyboardInterrupt:
        # This is normal when Ctrl+C is pressed
        logger.info("Server stopped by keyboard interrupt")
        # Exit cleanly
        sys.exit(0)
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Error running server: {e}", exc_info=True)
        # Exit with error code
        sys.exit(1)
