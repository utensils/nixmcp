"""
Home Manager context for MCP server.
"""

import logging
from typing import Dict, Any

# Get logger
logger = logging.getLogger("mcp_nixos")

# Import HomeManagerClient
from mcp_nixos.clients.home_manager_client import HomeManagerClient


class HomeManagerContext:
    """Provides Home Manager resources to AI models."""

    def __init__(self):
        """Initialize the Home Manager context."""
        self.hm_client = HomeManagerClient()
        logger.info("HomeManagerContext initialized")

        # Start loading the data in the background
        # This serves as a fallback in case eager loading fails
        self.hm_client.load_in_background()

    async def shutdown(self) -> None:
        """Shut down the Home Manager context cleanly.

        This is called during server shutdown.
        """
        logger.info("Shutting down Home Manager context")
        # Any cleanup needed for the Home Manager context

    def ensure_loaded(self, force_refresh: bool = False):
        """Ensure that data is loaded and available.

        This method can be called to eagerly load data during server initialization
        instead of relying on the background loading mechanism.

        Args:
            force_refresh: Whether to bypass cache and force a refresh from the web
        """
        logger.info("Ensuring Home Manager data is loaded...")
        self.hm_client.ensure_loaded(force_refresh=force_refresh)
        logger.info("Home Manager data is now loaded and available")

    def invalidate_cache(self):
        """Invalidate the disk cache for Home Manager data."""
        logger.info("Invalidating Home Manager data cache...")
        self.hm_client.invalidate_cache()
        logger.info("Home Manager data cache invalidated")

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

    def search_options(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for Home Manager options."""
        # Check if client is still loading or has an error
        if self.hm_client.loading_in_progress:
            logger.warning("Could not search options - data still loading")
            return {
                "count": 0,
                "options": [],
                "loading": True,
                "error": "Home Manager data is still loading in the background. Please try again in a few seconds.",
                "found": False,
            }
        elif self.hm_client.loading_error:
            logger.warning(f"Could not search options - loading failed: {self.hm_client.loading_error}")
            return {
                "count": 0,
                "options": [],
                "loading": False,
                "error": f"Failed to load Home Manager data: {self.hm_client.loading_error}",
                "found": False,
            }

        try:
            # Try to search without forcing a load
            return self.hm_client.search_options(query, limit)
        except Exception as e:
            # Handle other exceptions
            logger.warning(f"Could not search options: {str(e)}")
            return {
                "count": 0,
                "options": [],
                "loading": False,
                "error": f"Error searching Home Manager options: {str(e)}",
                "found": False,
            }

    def get_option(self, option_name: str) -> Dict[str, Any]:
        """Get information about a specific Home Manager option."""
        # Check if client is still loading or has an error
        if self.hm_client.loading_in_progress:
            logger.warning("Could not get option - data still loading")
            return {
                "name": option_name,
                "loading": True,
                "error": "Home Manager data is still loading in the background. Please try again in a few seconds.",
                "found": False,
            }
        elif self.hm_client.loading_error:
            logger.warning(f"Could not get option - loading failed: {self.hm_client.loading_error}")
            return {
                "name": option_name,
                "loading": False,
                "error": f"Failed to load Home Manager data: {self.hm_client.loading_error}",
                "found": False,
            }

        try:
            # Try to get option without forcing a load
            result = self.hm_client.get_option(option_name)

            # Ensure name is included in result for error messages
            if not result.get("found", False) and "name" not in result:
                result["name"] = option_name

            return result
        except Exception as e:
            # Handle other exceptions
            logger.warning(f"Could not get option: {str(e)}")
            return {
                "name": option_name,
                "loading": False,
                "error": f"Error retrieving Home Manager option: {str(e)}",
                "found": False,
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about Home Manager options."""
        # Check if client is still loading or has an error
        if self.hm_client.loading_in_progress:
            logger.warning("Could not get stats - data still loading")
            return {
                "total_options": 0,
                "loading": True,
                "error": "Home Manager data is still loading in the background. Please try again in a few seconds.",
                "found": False,
            }
        elif self.hm_client.loading_error:
            logger.warning(f"Could not get stats - loading failed: {self.hm_client.loading_error}")
            return {
                "total_options": 0,
                "loading": False,
                "error": f"Failed to load Home Manager data: {self.hm_client.loading_error}",
                "found": False,
            }

        try:
            # Try to get stats without forcing a load
            result = self.hm_client.get_stats()

            # Ensure we have a default value for total_options if not found
            if not result.get("found", True) and "total_options" not in result:
                result["total_options"] = 0

            return result
        except Exception as e:
            # Handle other exceptions
            logger.warning(f"Could not get stats: {str(e)}")
            return {
                "total_options": 0,
                "loading": False,
                "error": f"Error retrieving Home Manager statistics: {str(e)}",
                "found": False,
            }

    def get_options_list(self) -> Dict[str, Any]:
        """Get a hierarchical list of all top-level Home Manager options."""
        # Check if client is still loading or has an error
        if self.hm_client.loading_in_progress:
            logger.warning("Could not get options list - data still loading")
            return {
                "options": {},
                "count": 0,
                "loading": True,
                "error": "Home Manager data is still loading in the background. Please try again in a few seconds.",
                "found": False,
            }
        elif self.hm_client.loading_error:
            logger.warning(f"Could not get options list - loading failed: {self.hm_client.loading_error}")
            return {
                "options": {},
                "count": 0,
                "loading": False,
                "error": f"Failed to load Home Manager data: {self.hm_client.loading_error}",
                "found": False,
            }

        try:
            # Try to get options list without forcing a load
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

            # Create result with proper type structure
            options_dict: Dict[str, Dict[str, Any]] = {}
            result: Dict[str, Any] = {"options": options_dict}

            for option in top_level_options:
                # Get all options that start with this prefix
                options_data = self.get_options_by_prefix(option)
                if options_data.get("found", False):
                    options_dict[option] = {
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
                    options_dict[option] = {"count": 0, "enable_options": [], "types": {}, "has_children": False}

            # Set count and found flag on the result
            result["count"] = len(options_dict)
            result["found"] = True
            return result
        except Exception as e:
            logger.error(f"Error getting Home Manager options list: {str(e)}")
            return {"error": f"Failed to get options list: {str(e)}", "found": False}

    def get_options_by_prefix(self, option_prefix: str) -> Dict[str, Any]:
        """Get all options under a specific option prefix."""
        # Check if client is still loading or has an error
        if self.hm_client.loading_in_progress:
            logger.warning(f"Could not get options by prefix '{option_prefix}' - data still loading")
            return {
                "prefix": option_prefix,
                "count": 0,
                "options": [],
                "loading": True,
                "error": "Home Manager data is still loading in the background. Please try again in a few seconds.",
                "found": False,
            }
        elif self.hm_client.loading_error:
            logger.warning(
                f"Could not get options by prefix '{option_prefix}' - loading failed: {self.hm_client.loading_error}"
            )
            return {
                "prefix": option_prefix,
                "count": 0,
                "options": [],
                "loading": False,
                "error": f"Failed to load Home Manager data: {self.hm_client.loading_error}",
                "found": False,
            }

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
            logger.warning(f"Error getting Home Manager options by prefix '{option_prefix}': {str(e)}")
            return {
                "prefix": option_prefix,
                "options": [],
                "count": 0,
                "types": {},
                "enable_options": [],
                "loading": True,
                "error": "Home Manager data is still loading in the background. Please try again in a few seconds.",
                "found": False,
            }
