"""
Home Manager context for MCP server.
"""

import logging
from typing import Dict, Any

# Get logger
logger = logging.getLogger("nixmcp")

# Import HomeManagerClient
from nixmcp.clients.home_manager_client import HomeManagerClient


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

    def search_options(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for Home Manager options."""
        # Check if data is still being loaded
        with self.hm_client.loading_lock:
            if not self.hm_client.is_loaded and self.hm_client.loading_in_progress:
                # Return a loading status instead of waiting indefinitely
                return {
                    "loading": True,
                    "error": "Home Manager data is still being loaded. Please try again in a moment.",
                    "found": False,
                    "count": 0,
                    "options": [],
                }

            # If loading failed, report the error
            if self.hm_client.loading_error:
                return {
                    "loading": False,
                    "error": f"Failed to load Home Manager data: {self.hm_client.loading_error}",
                    "found": False,
                    "count": 0,
                    "options": [],
                }

        # Ensure we have the client and it's not loading
        if not hasattr(self, "hm_client") or not self.hm_client:
            return {
                "loading": False,
                "error": "Home Manager client not initialized",
                "found": False,
                "count": 0,
                "options": [],
            }

        return self.hm_client.search_options(query, limit)

    def get_option(self, option_name: str) -> Dict[str, Any]:
        """Get information about a specific Home Manager option."""
        # Check if data is still being loaded
        with self.hm_client.loading_lock:
            if not self.hm_client.is_loaded and self.hm_client.loading_in_progress:
                # Return a loading status instead of waiting indefinitely
                return {
                    "loading": True,
                    "error": "Home Manager data is still being loaded. Please try again in a moment.",
                    "found": False,
                    "name": option_name,
                }

            # If loading failed, report the error
            if self.hm_client.loading_error:
                return {
                    "loading": False,
                    "error": f"Failed to load Home Manager data: {self.hm_client.loading_error}",
                    "found": False,
                    "name": option_name,
                }

        # Ensure we have the client and it's not loading
        if not hasattr(self, "hm_client") or not self.hm_client:
            return {
                "loading": False,
                "error": "Home Manager client not initialized",
                "found": False,
                "name": option_name,
            }

        return self.hm_client.get_option(option_name)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about Home Manager options."""
        # Check if data is still being loaded
        with self.hm_client.loading_lock:
            if not self.hm_client.is_loaded and self.hm_client.loading_in_progress:
                # Return a loading status instead of waiting indefinitely
                return {
                    "loading": True,
                    "error": "Home Manager data is still being loaded. Please try again in a moment.",
                    "found": False,
                    "total_options": 0,
                }

            # If loading failed, report the error
            if self.hm_client.loading_error:
                return {
                    "loading": False,
                    "error": f"Failed to load Home Manager data: {self.hm_client.loading_error}",
                    "found": False,
                    "total_options": 0,
                }

        # Ensure we have the client and it's not loading
        if not hasattr(self, "hm_client") or not self.hm_client:
            return {
                "loading": False,
                "error": "Home Manager client not initialized",
                "found": False,
                "total_options": 0,
            }

        return self.hm_client.get_stats()

    def get_options_list(self) -> Dict[str, Any]:
        """Get a hierarchical list of all top-level Home Manager options."""
        try:
            # Check if data is still being loaded
            with self.hm_client.loading_lock:
                if not self.hm_client.is_loaded and self.hm_client.loading_in_progress:
                    # Return a loading status instead of waiting indefinitely
                    return {
                        "loading": True,
                        "error": "Home Manager data is still being loaded. Please try again in a moment.",
                        "found": False,
                    }

                # If loading failed, report the error
                if self.hm_client.loading_error:
                    return {
                        "loading": False,
                        "error": f"Failed to load Home Manager data: {self.hm_client.loading_error}",
                        "found": False,
                    }

                # Ensure the client is loaded and ready
                if not self.hm_client.is_loaded:
                    return {"loading": False, "error": "Home Manager client data is not loaded", "found": False}

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

    def get_options_by_prefix(self, option_prefix: str) -> Dict[str, Any]:
        """Get all options under a specific option prefix."""
        try:
            # Check if data is still being loaded
            with self.hm_client.loading_lock:
                if not self.hm_client.is_loaded and self.hm_client.loading_in_progress:
                    # Return a loading status instead of waiting indefinitely
                    return {
                        "loading": True,
                        "error": "Home Manager data is still being loaded. Please try again in a moment.",
                        "found": False,
                    }

                # If loading failed, report the error
                if self.hm_client.loading_error:
                    return {
                        "loading": False,
                        "error": f"Failed to load Home Manager data: {self.hm_client.loading_error}",
                        "found": False,
                    }

                # Ensure the client is loaded and ready
                if not self.hm_client.is_loaded:
                    return {"loading": False, "error": "Home Manager client data is not loaded", "found": False}

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
