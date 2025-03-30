"""
NixOS context for MCP server.
"""

import logging
from typing import Any, Dict, List, Optional

from mcp_nixos import __version__
from mcp_nixos.clients.elasticsearch_client import ElasticsearchClient

logger = logging.getLogger("mcp_nixos")


class NixOSContext:
    """Provides NixOS resources to AI models."""

    def __init__(self):
        """Initialize the ModelContext."""
        self.es_client = ElasticsearchClient()
        logger.info("NixOSContext initialized")

    async def shutdown(self) -> None:
        """Shut down the NixOS context cleanly.

        This is called during server shutdown.
        """
        logger.info("Shutting down NixOS context")
        # Any cleanup needed for the NixOS context

    def get_status(self) -> Dict[str, Any]:
        """Get the status of the MCP-NixOS server."""
        return {
            "status": "ok",
            "version": __version__,
            "name": "MCP-NixOS",
            "description": "NixOS Model Context Protocol Server",
            "server_type": "http",
            "cache_stats": self.es_client.cache.get_stats(),
        }

    def get_package(self, package_name: str, channel: str = "unstable") -> Dict[str, Any]:
        """Get information about a NixOS package."""
        try:
            return self.es_client.get_package(package_name, channel=channel)
        except Exception as e:
            logger.error(f"Error fetching package {package_name}: {e}")
            return {"name": package_name, "error": f"Failed to fetch package: {str(e)}", "found": False}

    def search_packages(self, query: str, limit: int = 20, channel: str = "unstable") -> Dict[str, Any]:
        """Search for NixOS packages."""
        try:
            return self.es_client.search_packages(query, limit, channel=channel)
        except Exception as e:
            logger.error(f"Error searching packages for query {query}: {e}")
            return {"count": 0, "packages": [], "error": f"Failed to search packages: {str(e)}"}

    def search_options(
        self,
        query: str,
        limit: int = 20,
        channel: str = "unstable",
        additional_terms: Optional[List[str]] = None,
        quoted_terms: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Search for NixOS options with enhanced multi-word query support.

        Args:
            query: The main search query (hierarchical path or term)
            limit: Maximum number of results
            channel: NixOS channel to search in (unstable or stable)
            additional_terms: Additional terms for filtering results
            quoted_terms: Phrases that should be matched exactly

        Returns:
            Dictionary with search results
        """
        try:
            return self.es_client.search_options(
                query,
                limit=limit,
                channel=channel,
                additional_terms=additional_terms or [],
                quoted_terms=quoted_terms or [],
            )
        except Exception as e:
            logger.error(f"Error searching options for query {query}: {e}")
            return {"count": 0, "options": [], "error": f"Failed to search options: {str(e)}"}

    def get_option(self, option_name: str, channel: str = "unstable") -> Dict[str, Any]:
        """Get information about a NixOS option."""
        try:
            return self.es_client.get_option(option_name, channel=channel)
        except Exception as e:
            logger.error(f"Error fetching option {option_name}: {e}")
            return {"name": option_name, "error": f"Failed to fetch option: {str(e)}", "found": False}

    def search_programs(self, program: str, limit: int = 20, channel: str = "unstable") -> Dict[str, Any]:
        """Search for packages that provide specific programs."""
        try:
            return self.es_client.search_programs(program, limit, channel=channel)
        except Exception as e:
            logger.error(f"Error searching programs for query {program}: {e}")
            return {"count": 0, "packages": [], "error": f"Failed to search programs: {str(e)}"}

    def search_packages_with_version(
        self, query: str, version_pattern: str, limit: int = 20, channel: str = "unstable"
    ) -> Dict[str, Any]:
        """Search for packages with a specific version pattern."""
        try:
            return self.es_client.search_packages_with_version(query, version_pattern, limit, channel=channel)
        except Exception as e:
            logger.error(f"Error searching packages with version pattern for query {query}: {e}")
            return {"count": 0, "packages": [], "error": f"Failed to search packages with version: {str(e)}"}

    def advanced_query(
        self, index_type: str, query_string: str, limit: int = 20, channel: str = "unstable"
    ) -> Dict[str, Any]:
        """Execute an advanced query using Elasticsearch's query string syntax."""
        try:
            return self.es_client.advanced_query(index_type, query_string, limit, channel=channel)
        except Exception as e:
            logger.error(f"Error executing advanced query {query_string}: {e}")
            return {"error": f"Failed to execute advanced query: {str(e)}", "hits": {"hits": [], "total": {"value": 0}}}

    def get_package_stats(self, channel: str = "unstable") -> Dict[str, Any]:
        """Get statistics about NixOS packages."""
        try:
            return self.es_client.get_package_stats(channel=channel)
        except Exception as e:
            logger.error(f"Error getting package stats: {e}")
            return {
                "error": f"Failed to get package statistics: {str(e)}",
                "aggregations": {
                    "channels": {"buckets": []},
                    "licenses": {"buckets": []},
                    "platforms": {"buckets": []},
                },
            }

    def count_options(self, channel: str = "unstable") -> Dict[str, Any]:
        """Get an accurate count of NixOS options."""
        try:
            return self.es_client.count_options(channel=channel)
        except Exception as e:
            logger.error(f"Error counting options: {e}")
            return {"count": 0, "error": f"Failed to count options: {str(e)}"}
