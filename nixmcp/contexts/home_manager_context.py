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
        return self.hm_client.search_options(query, limit)

    def get_option(self, option_name: str) -> Dict[str, Any]:
        """Get information about a specific Home Manager option."""
        return self.hm_client.get_option(option_name)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about Home Manager options."""
        return self.hm_client.get_stats()
