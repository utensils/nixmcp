"""
MCP resources for NixOS.
"""

import logging
from typing import Any, Callable, Dict

# Get logger
logger = logging.getLogger("mcp_nixos")


def nixos_status_resource(nixos_context) -> Dict[str, Any]:
    """Get the status of the MCP-NixOS server."""
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

    # Register status resource
    @mcp.resource("nixos://status")
    def status_resource_handler():
        return nixos_status_resource(get_nixos_context())

    # Register package resource
    @mcp.resource("nixos://package/{package_name}")
    def package_resource_handler(package_name: str):
        return package_resource(package_name, get_nixos_context())

    # Register search packages resource
    @mcp.resource("nixos://search/packages/{query}")
    def search_packages_resource_handler(query: str):
        return search_packages_resource(query, get_nixos_context())

    # Register search options resource
    @mcp.resource("nixos://search/options/{query}")
    def search_options_resource_handler(query: str):
        return search_options_resource(query, get_nixos_context())

    # Register option resource
    @mcp.resource("nixos://option/{option_name}")
    def option_resource_handler(option_name: str):
        return option_resource(option_name, get_nixos_context())

    # Register search programs resource
    @mcp.resource("nixos://search/programs/{program}")
    def search_programs_resource_handler(program: str):
        return search_programs_resource(program, get_nixos_context())

    # Register package stats resource
    @mcp.resource("nixos://packages/stats")
    def package_stats_resource_handler():
        return package_stats_resource(get_nixos_context())
