"""
Home Manager context for MCP server.
"""

import logging
from typing import Dict, Any

# Get logger
logger = logging.getLogger("nixmcp")

# Import HomeManagerClient and helpers
from nixmcp.clients.home_manager_client import HomeManagerClient
from nixmcp.utils.helpers import check_loading_status


class HomeManagerContext:
    """Provides Home Manager resources to AI models."""

    def __init__(self):
        """Initialize the Home Manager context."""
        self.hm_client = HomeManagerClient()
        logger.info("HomeManagerContext initialized")

        # Start loading the data in the background
        self.hm_client.load_in_background()

    def get_status(self) -> Dict[str, Any]:
        """Get the status of the Home Manager context."""
        try:
            # Try to get statistics without forcing a load
            with self.hm_client.loading_lock:
                if self.hm_client.is_loaded:
                    stats = self.hm_client.get_stats()
                    return {
                        "status": "ok",
                        "loaded": True,
                        "options_count": stats.get("total_options", 0),
                        "cache_stats": self.hm_client.cache.get_stats(),
                    }
                elif self.hm_client.loading_error:
                    return {
                        "status": "error",
                        "loaded": False,
                        "error": self.hm_client.loading_error,
                        "cache_stats": self.hm_client.cache.get_stats(),
                    }
                else:
                    return {
                        "status": "loading",
                        "loaded": False,
                        "cache_stats": self.hm_client.cache.get_stats(),
                    }
        except Exception as e:
            logger.error(f"Error getting Home Manager status: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "loaded": False,
            }

    @check_loading_status
    def search_options(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for Home Manager options."""
        return self.hm_client.search_options(query, limit)

    @check_loading_status
    def get_option(self, option_name: str) -> Dict[str, Any]:
        """Get information about a specific Home Manager option."""
        result = self.hm_client.get_option(option_name)

        # Ensure name is included in result for error messages
        if not result.get("found", False) and "name" not in result:
            result["name"] = option_name

        return result

    @check_loading_status
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about Home Manager options."""
        result = self.hm_client.get_stats()

        # Ensure we have a default value for total_options if not found
        if not result.get("found", True) and "total_options" not in result:
            result["total_options"] = 0

        return result

    @check_loading_status
    def get_options_list(self) -> Dict[str, Any]:
        """Get a hierarchical list of all top-level Home Manager options."""
        try:
            top_level_options = [
                "programs",
                "services",
                "home",
                "accounts",
                "fonts",
                "gtk",
                "qt",
                "xdg",
                "wayland",
                "i18n",
                "manual",
                "news",
                "nix",
                "nixpkgs",
                "systemd",
                "targets",
                "dconf",
                "editorconfig",
                "lib",
                "launchd",
                "pam",
                "sops",
                "windowManager",
                "xresources",
                "xsession",
            ]

            result = {"options": {}}

            for option in top_level_options:
                # Get all options that start with this prefix
                options_data = self.get_options_by_prefix(option)
                if options_data.get("found", False):
                    result["options"][option] = {
                        "count": options_data.get("count", 0),
                        "enable_options": options_data.get("enable_options", []),
                        "types": options_data.get("types", {}),
                        "has_children": options_data.get("count", 0) > 0,
                    }
                else:
                    # Check if still loading
                    if options_data.get("loading", False):
                        return options_data

                    # Include the option even if no matches found
                    result["options"][option] = {"count": 0, "enable_options": [], "types": {}, "has_children": False}

            result["count"] = len(result["options"])
            result["found"] = True
            return result
        except Exception as e:
            logger.error(f"Error getting Home Manager options list: {str(e)}")
            return {"error": f"Failed to get options list: {str(e)}", "found": False}

    @check_loading_status
    def get_options_by_prefix(self, option_prefix: str) -> Dict[str, Any]:
        """Get all options under a specific option prefix."""
        try:
            # Search with wildcard to get all options under this prefix
            search_query = f"{option_prefix}.*"
            search_results = self.hm_client.search_options(search_query, limit=500)

            # Add found=False if not already present
            if "found" not in search_results:
                search_results["found"] = search_results.get("count", 0) > 0

            if not search_results.get("found", False):
                return {"error": f"No options found with prefix '{option_prefix}'", "found": False}

            options = search_results.get("options", [])

            # Count option types
            type_counts = {}
            enable_options = []

            for option in options:
                option_type = option.get("type", "unknown")
                if option_type not in type_counts:
                    type_counts[option_type] = 0
                type_counts[option_type] += 1

                # Collect "enable" options which are typically boolean and used to enable features
                option_name = option.get("name", "")
                if option_name.endswith(".enable") and option.get("type") == "boolean":
                    # Extract just the service/program name from the full path
                    parts = option_name.split(".")
                    if len(parts) >= 3:  # e.g., ["programs", "git", "enable"]
                        parent = parts[-2]
                        enable_options.append(
                            {"name": option_name, "parent": parent, "description": option.get("description", "")}
                        )

            return {
                "prefix": option_prefix,
                "options": options,
                "count": len(options),
                "types": type_counts,
                "enable_options": enable_options,
                "found": True,
            }

        except Exception as e:
            logger.error(f"Error getting Home Manager options by prefix '{option_prefix}': {str(e)}")
            return {"error": f"Failed to get options with prefix '{option_prefix}': {str(e)}", "found": False}
