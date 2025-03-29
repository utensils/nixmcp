"""
MCP resources for Home Manager.
"""

import logging
from typing import Dict, Any, Callable

# Get logger
logger = logging.getLogger("mcp_nixos")


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


def home_manager_options_list_resource(home_manager_context) -> Dict[str, Any]:
    """Get a hierarchical list of all top-level Home Manager options."""
    logger.info("Handling Home Manager options list resource request")
    return home_manager_context.get_options_list()


def home_manager_options_by_prefix_resource(option_prefix: str, home_manager_context) -> Dict[str, Any]:
    """Get all options under a specific option prefix."""
    logger.info(f"Handling Home Manager options by prefix request for {option_prefix}")
    return home_manager_context.get_options_by_prefix(option_prefix)


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

    # Register options list resource
    @mcp.resource("home-manager://options/list")
    def home_manager_options_list_resource_handler():
        return home_manager_options_list_resource(get_home_manager_context())

    # Register resource for programs
    @mcp.resource("home-manager://options/programs")
    def home_manager_options_programs_handler():
        return home_manager_options_by_prefix_resource("programs", get_home_manager_context())

    # Register resource for services
    @mcp.resource("home-manager://options/services")
    def home_manager_options_services_handler():
        return home_manager_options_by_prefix_resource("services", get_home_manager_context())

    # Register resource for home
    @mcp.resource("home-manager://options/home")
    def home_manager_options_home_handler():
        return home_manager_options_by_prefix_resource("home", get_home_manager_context())

    # Register resource for accounts
    @mcp.resource("home-manager://options/accounts")
    def home_manager_options_accounts_handler():
        return home_manager_options_by_prefix_resource("accounts", get_home_manager_context())

    # Register resource for fonts
    @mcp.resource("home-manager://options/fonts")
    def home_manager_options_fonts_handler():
        return home_manager_options_by_prefix_resource("fonts", get_home_manager_context())

    # Register resource for gtk
    @mcp.resource("home-manager://options/gtk")
    def home_manager_options_gtk_handler():
        return home_manager_options_by_prefix_resource("gtk", get_home_manager_context())

    # Register resource for qt
    @mcp.resource("home-manager://options/qt")
    def home_manager_options_qt_handler():
        return home_manager_options_by_prefix_resource("qt", get_home_manager_context())

    # Register resource for xdg
    @mcp.resource("home-manager://options/xdg")
    def home_manager_options_xdg_handler():
        return home_manager_options_by_prefix_resource("xdg", get_home_manager_context())

    # Register resource for wayland
    @mcp.resource("home-manager://options/wayland")
    def home_manager_options_wayland_handler():
        return home_manager_options_by_prefix_resource("wayland", get_home_manager_context())

    # Register resource for i18n
    @mcp.resource("home-manager://options/i18n")
    def home_manager_options_i18n_handler():
        return home_manager_options_by_prefix_resource("i18n", get_home_manager_context())

    # Register resource for manual
    @mcp.resource("home-manager://options/manual")
    def home_manager_options_manual_handler():
        return home_manager_options_by_prefix_resource("manual", get_home_manager_context())

    # Register resource for news
    @mcp.resource("home-manager://options/news")
    def home_manager_options_news_handler():
        return home_manager_options_by_prefix_resource("news", get_home_manager_context())

    # Register resource for nix
    @mcp.resource("home-manager://options/nix")
    def home_manager_options_nix_handler():
        return home_manager_options_by_prefix_resource("nix", get_home_manager_context())

    # Register resource for nixpkgs
    @mcp.resource("home-manager://options/nixpkgs")
    def home_manager_options_nixpkgs_handler():
        return home_manager_options_by_prefix_resource("nixpkgs", get_home_manager_context())

    # Register resource for systemd
    @mcp.resource("home-manager://options/systemd")
    def home_manager_options_systemd_handler():
        return home_manager_options_by_prefix_resource("systemd", get_home_manager_context())

    # Register resource for targets
    @mcp.resource("home-manager://options/targets")
    def home_manager_options_targets_handler():
        return home_manager_options_by_prefix_resource("targets", get_home_manager_context())

    # Register resource for dconf
    @mcp.resource("home-manager://options/dconf")
    def home_manager_options_dconf_handler():
        return home_manager_options_by_prefix_resource("dconf", get_home_manager_context())

    # Register resource for editorconfig
    @mcp.resource("home-manager://options/editorconfig")
    def home_manager_options_editorconfig_handler():
        return home_manager_options_by_prefix_resource("editorconfig", get_home_manager_context())

    # Register resource for lib
    @mcp.resource("home-manager://options/lib")
    def home_manager_options_lib_handler():
        return home_manager_options_by_prefix_resource("lib", get_home_manager_context())

    # Register resource for launchd
    @mcp.resource("home-manager://options/launchd")
    def home_manager_options_launchd_handler():
        return home_manager_options_by_prefix_resource("launchd", get_home_manager_context())

    # Register resource for pam
    @mcp.resource("home-manager://options/pam")
    def home_manager_options_pam_handler():
        return home_manager_options_by_prefix_resource("pam", get_home_manager_context())

    # Register resource for sops
    @mcp.resource("home-manager://options/sops")
    def home_manager_options_sops_handler():
        return home_manager_options_by_prefix_resource("sops", get_home_manager_context())

    # Register resource for windowManager
    @mcp.resource("home-manager://options/windowManager")
    def home_manager_options_windowManager_handler():
        return home_manager_options_by_prefix_resource("windowManager", get_home_manager_context())

    # Register resource for xresources
    @mcp.resource("home-manager://options/xresources")
    def home_manager_options_xresources_handler():
        return home_manager_options_by_prefix_resource("xresources", get_home_manager_context())

    # Register resource for xsession
    @mcp.resource("home-manager://options/xsession")
    def home_manager_options_xsession_handler():
        return home_manager_options_by_prefix_resource("xsession", get_home_manager_context())

    # Keep a generic endpoint for other prefixes and nested paths
    @mcp.resource("home-manager://options/prefix/{option_prefix}")
    def home_manager_options_by_prefix_resource_handler(option_prefix: str):
        return home_manager_options_by_prefix_resource(option_prefix, get_home_manager_context())
