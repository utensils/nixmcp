"""Darwin resources for MCP."""

import logging
from typing import Any, Dict, Optional

from mcp_nixos.contexts.darwin.darwin_context import DarwinContext
from mcp_nixos.utils.helpers import get_context_or_fallback

logger = logging.getLogger(__name__)

# Global context instance
darwin_context: Optional[DarwinContext] = None


def register_darwin_resources(context: Optional[DarwinContext] = None, mcp=None) -> None:
    """Register Darwin resources with MCP.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.
        mcp: The MCP server instance to register resources with.
    """
    global darwin_context
    darwin_context = context

    # Register resources with MCP if we have an MCP instance
    if mcp:
        # Register status resource
        @mcp.resource("darwin://status")
        def status_resource_handler():
            return get_darwin_status(context)

        # Register search options resource
        @mcp.resource("darwin://search/options/{query}")
        def search_options_handler(query: str):
            return search_darwin_options(query, context=context)

        # Register option resource
        @mcp.resource("darwin://option/{option_name}")
        def option_handler(option_name: str):
            return get_darwin_option(option_name, context=context)

        # Register stats resource
        @mcp.resource("darwin://options/stats")
        def stats_handler():
            return get_darwin_statistics(context=context)

        # Register categories resource
        @mcp.resource("darwin://options/categories")
        def categories_handler():
            return get_darwin_categories(context=context)

        # Register options by prefix resource
        @mcp.resource("darwin://options/prefix/{option_prefix}")
        def options_by_prefix_handler(option_prefix: str):
            return get_darwin_options_by_prefix(option_prefix, context=context)


def get_darwin_status(context=None) -> Dict[str, Any]:
    """Get status information about the Darwin context.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Status information.
    """
    try:
        ctx = get_context_or_fallback(context, "darwin_context")
        if not ctx:
            return {
                "error": "No Darwin context available",
                "status": "error",
                "options_count": 0,
                "categories_count": 0,
            }
        return ctx.get_status()
    except Exception as e:
        logger.error(f"Error getting Darwin status: {e}")
        return {
            "error": str(e),
            "status": "error",
            "options_count": 0,
            "categories_count": 0,
        }


def search_darwin_options(query: str, limit: int = 20, context=None) -> Dict[str, Any]:
    """Search for Darwin options.

    Args:
        query: Search query.
        limit: Maximum number of results to return.
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Search results.
    """
    try:
        ctx = get_context_or_fallback(context, "darwin_context")
        if not ctx:
            return {
                "error": "No Darwin context available",
                "query": query,
                "limit": limit,
                "count": 0,
                "results": [],
                "found": False,
            }

        results = ctx.search_options(query, limit=limit)

        return {
            "query": query,
            "limit": limit,
            "count": len(results),
            "results": results,
            "found": len(results) > 0,
        }
    except Exception as e:
        logger.error(f"Error searching Darwin options: {e}")
        return {
            "error": str(e),
            "query": query,
            "limit": limit,
            "count": 0,
            "results": [],
            "found": False,
        }


def get_darwin_option(option_name: str, context=None) -> Dict[str, Any]:
    """Get a Darwin option by name.

    Args:
        option_name: Option name.
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Option information.
    """
    try:
        ctx = get_context_or_fallback(context, "darwin_context")
        if not ctx:
            return {
                "error": "No Darwin context available",
                "name": option_name,
                "found": False,
            }

        option = ctx.get_option(option_name)

        if not option:
            return {
                "error": f"Option '{option_name}' not found",
                "name": option_name,
                "found": False,
            }

        return {
            "name": option_name,
            "option": option,
            "found": True,
        }
    except Exception as e:
        logger.error(f"Error getting Darwin option {option_name}: {e}")
        return {
            "error": str(e),
            "name": option_name,
            "found": False,
        }


def get_darwin_statistics(context=None) -> Dict[str, Any]:
    """Get statistics about Darwin options.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Statistics information.
    """
    try:
        ctx = get_context_or_fallback(context, "darwin_context")
        if not ctx:
            return {
                "error": "No Darwin context available",
                "found": False,
            }

        stats = ctx.get_statistics()

        return {
            "statistics": stats,
            "found": True,
        }
    except Exception as e:
        logger.error(f"Error getting Darwin statistics: {e}")
        return {
            "error": str(e),
            "found": False,
        }


def get_darwin_categories(context=None) -> Dict[str, Any]:
    """Get top-level Darwin option categories.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Categories information.
    """
    try:
        ctx = get_context_or_fallback(context, "darwin_context")
        if not ctx:
            return {
                "error": "No Darwin context available",
                "categories": [],
                "count": 0,
                "found": False,
            }

        categories = ctx.get_categories()

        return {
            "categories": categories,
            "count": len(categories),
            "found": True,
        }
    except Exception as e:
        logger.error(f"Error getting Darwin categories: {e}")
        return {
            "error": str(e),
            "categories": [],
            "count": 0,
            "found": False,
        }


def get_darwin_options_by_prefix(option_prefix: str, context=None) -> Dict[str, Any]:
    """Get Darwin options by prefix.

    Args:
        option_prefix: Option prefix.
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Options information.
    """
    try:
        ctx = get_context_or_fallback(context, "darwin_context")
        if not ctx:
            return {
                "error": "No Darwin context available",
                "prefix": option_prefix,
                "options": [],
                "count": 0,
                "found": False,
            }

        options = ctx.get_options_by_prefix(option_prefix)

        return {
            "prefix": option_prefix,
            "options": options,
            "count": len(options),
            "found": len(options) > 0,
        }
    except Exception as e:
        logger.error(f"Error getting Darwin options by prefix {option_prefix}: {e}")
        return {
            "error": str(e),
            "prefix": option_prefix,
            "options": [],
            "count": 0,
            "found": False,
        }


# Category-specific resources


def _get_options_by_category(category: str, context=None) -> Dict[str, Any]:
    """Get options by category.

    Args:
        category: Category name.
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Options information.
    """
    return get_darwin_options_by_prefix(category, context)


def get_darwin_documentation_options(context=None) -> Dict[str, Any]:
    """Get Darwin documentation options.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Documentation options.
    """
    return _get_options_by_category("documentation", context)


def get_darwin_environment_options(context=None) -> Dict[str, Any]:
    """Get Darwin environment options.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Environment options.
    """
    return _get_options_by_category("environment", context)


def get_darwin_fonts_options(context=None) -> Dict[str, Any]:
    """Get Darwin fonts options.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Fonts options.
    """
    return _get_options_by_category("fonts", context)


def get_darwin_homebrew_options(context=None) -> Dict[str, Any]:
    """Get Darwin homebrew options.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Homebrew options.
    """
    return _get_options_by_category("homebrew", context)


def get_darwin_launchd_options(context=None) -> Dict[str, Any]:
    """Get Darwin launchd options.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Launchd options.
    """
    return _get_options_by_category("launchd", context)


def get_darwin_networking_options(context=None) -> Dict[str, Any]:
    """Get Darwin networking options.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Networking options.
    """
    return _get_options_by_category("networking", context)


def get_darwin_nix_options(context=None) -> Dict[str, Any]:
    """Get Darwin nix options.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Nix options.
    """
    return _get_options_by_category("nix", context)


def get_darwin_nixpkgs_options(context=None) -> Dict[str, Any]:
    """Get Darwin nixpkgs options.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Nixpkgs options.
    """
    return _get_options_by_category("nixpkgs", context)


def get_darwin_power_options(context=None) -> Dict[str, Any]:
    """Get Darwin power options.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Power options.
    """
    return _get_options_by_category("power", context)


def get_darwin_programs_options(context=None) -> Dict[str, Any]:
    """Get Darwin programs options.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Programs options.
    """
    return _get_options_by_category("programs", context)


def get_darwin_security_options(context=None) -> Dict[str, Any]:
    """Get Darwin security options.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Security options.
    """
    return _get_options_by_category("security", context)


def get_darwin_services_options(context=None) -> Dict[str, Any]:
    """Get Darwin services options.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Services options.
    """
    return _get_options_by_category("services", context)


def get_darwin_system_options(context=None) -> Dict[str, Any]:
    """Get Darwin system options.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        System options.
    """
    return _get_options_by_category("system", context)


def get_darwin_time_options(context=None) -> Dict[str, Any]:
    """Get Darwin time options.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Time options.
    """
    return _get_options_by_category("time", context)


def get_darwin_users_options(context=None) -> Dict[str, Any]:
    """Get Darwin users options.

    Args:
        context: Optional DarwinContext to use. If not provided, the global context is used.

    Returns:
        Users options.
    """
    return _get_options_by_category("users", context)
