"""
MCP resources for NixOS.
"""

import logging
from typing import Dict, Any, Optional, Callable

# Get logger
logger = logging.getLogger("nixmcp")


def nixos_status_resource(nixos_context) -> Dict[str, Any]:
    """Get the status of the NixMCP server."""
    logger.info("Handling NixOS status resource request")
    return nixos_context.get_status()


def package_resource(package_name: str, nixos_context) -> Dict[str, Any]:
    """Get information about a NixOS package."""
    logger.info(f"Handling package resource request for {package_name}")
    return nixos_context.get_package(package_name)


def search_packages_resource(query: str, nixos_context) -> Dict[str, Any]:
    """Search for NixOS packages."""
    logger.info(f"Handling package search request for {query}")
    return nixos_context.search_packages(query)


def search_options_resource(query: str, nixos_context) -> Dict[str, Any]:
    """Search for NixOS options."""
    logger.info(f"Handling option search request for {query}")
    return nixos_context.search_options(query)


def option_resource(option_name: str, nixos_context) -> Dict[str, Any]:
    """Get information about a NixOS option."""
    logger.info(f"Handling option resource request for {option_name}")
    return nixos_context.get_option(option_name)


def search_programs_resource(program: str, nixos_context) -> Dict[str, Any]:
    """Search for packages that provide specific programs."""
    logger.info(f"Handling program search request for {program}")
    return nixos_context.search_programs(program)


def package_stats_resource(nixos_context) -> Dict[str, Any]:
    """Get statistics about NixOS packages."""
    logger.info("Handling package statistics resource request")
    return nixos_context.get_package_stats()


def register_nixos_resources(mcp, get_nixos_context: Callable[[], Any]) -> None:
    """
    Register all NixOS resources with the MCP server.
    
    Args:
        mcp: The MCP server instance
        get_nixos_context: A function that returns the NixOS context
    """
    # Define a decorator to inject the NixOS context
    def with_nixos_context(handler):
        def wrapper(*args, **kwargs):
            return handler(*args, nixos_context=get_nixos_context(), **kwargs)
        return wrapper
    
    # Register resources with context injection
    mcp.resource("nixos://status")(with_nixos_context(nixos_status_resource))
    mcp.resource("nixos://package/{package_name}")(with_nixos_context(package_resource))
    mcp.resource("nixos://search/packages/{query}")(with_nixos_context(search_packages_resource))
    mcp.resource("nixos://search/options/{query}")(with_nixos_context(search_options_resource))
    mcp.resource("nixos://option/{option_name}")(with_nixos_context(option_resource))
    mcp.resource("nixos://search/programs/{program}")(with_nixos_context(search_programs_resource))
    mcp.resource("nixos://packages/stats")(with_nixos_context(package_stats_resource))