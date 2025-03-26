"""
MCP resources for Home Manager.
"""

import logging
from typing import Dict, Any, Callable

# Get logger
logger = logging.getLogger("nixmcp")


def home_manager_status_resource(home_manager_context) -> Dict[str, Any]:
    """Get the status of the Home Manager context."""
    logger.info("Handling Home Manager status resource request")
    return home_manager_context.get_status()


def home_manager_search_options_resource(query: str, home_manager_context) -> Dict[str, Any]:
    """Search for Home Manager options."""
    logger.info(f"Handling Home Manager option search request for {query}")
    return home_manager_context.search_options(query)


def home_manager_option_resource(option_name: str, home_manager_context) -> Dict[str, Any]:
    """Get information about a Home Manager option."""
    logger.info(f"Handling Home Manager option resource request for {option_name}")
    return home_manager_context.get_option(option_name)


def home_manager_stats_resource(home_manager_context) -> Dict[str, Any]:
    """Get statistics about Home Manager options."""
    logger.info("Handling Home Manager statistics resource request")
    return home_manager_context.get_stats()


def register_home_manager_resources(mcp, get_home_manager_context: Callable[[], Any]) -> None:
    """
    Register all Home Manager resources with the MCP server.

    Args:
        mcp: The MCP server instance
        get_home_manager_context: A function that returns the Home Manager context
    """

    # Register status resource
    @mcp.resource("home-manager://status")
    def home_manager_status_resource_handler():
        return home_manager_status_resource(get_home_manager_context())

    # Register search options resource
    @mcp.resource("home-manager://search/options/{query}")
    def home_manager_search_options_resource_handler(query: str):
        return home_manager_search_options_resource(query, get_home_manager_context())

    # Register option resource
    @mcp.resource("home-manager://option/{option_name}")
    def home_manager_option_resource_handler(option_name: str):
        return home_manager_option_resource(option_name, get_home_manager_context())

    # Register stats resource
    @mcp.resource("home-manager://options/stats")
    def home_manager_stats_resource_handler():
        return home_manager_stats_resource(get_home_manager_context())
