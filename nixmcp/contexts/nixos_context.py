"""
NixOS context for MCP server.
"""

import logging
from typing import Dict, Any

# Get logger
logger = logging.getLogger("nixmcp")

# Import ElasticsearchClient
from nixmcp.clients.elasticsearch_client import ElasticsearchClient

# Import version
from nixmcp import __version__


class NixOSContext:
    """Provides NixOS resources to AI models."""

    def __init__(self):
        """Initialize the ModelContext."""
        self.es_client = ElasticsearchClient()
        logger.info("NixOSContext initialized")

    def get_status(self) -> Dict[str, Any]:
        """Get the status of the NixMCP server."""
        return {
            "status": "ok",
            "version": __version__,
            "name": "NixMCP",
            "description": "NixOS Model Context Protocol Server",
            "server_type": "http",
            "cache_stats": self.es_client.cache.get_stats(),
        }

    def get_package(self, package_name: str) -> Dict[str, Any]:
        """Get information about a NixOS package."""
        return self.es_client.get_package(package_name)

    def search_packages(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for NixOS packages."""
        return self.es_client.search_packages(query, limit)

    def search_options(
        self, query: str, limit: int = 10, additional_terms: list = None, quoted_terms: list = None
    ) -> Dict[str, Any]:
        """Search for NixOS options with enhanced multi-word query support.

        Args:
            query: The main search query (hierarchical path or term)
            limit: Maximum number of results
            additional_terms: Additional terms for filtering results
            quoted_terms: Phrases that should be matched exactly

        Returns:
            Dictionary with search results
        """
        return self.es_client.search_options(
            query, limit=limit, additional_terms=additional_terms or [], quoted_terms=quoted_terms or []
        )

    def get_option(self, option_name: str) -> Dict[str, Any]:
        """Get information about a NixOS option."""
        return self.es_client.get_option(option_name)

    def search_programs(self, program: str, limit: int = 10) -> Dict[str, Any]:
        """Search for packages that provide specific programs."""
        return self.es_client.search_programs(program, limit)

    def search_packages_with_version(self, query: str, version_pattern: str, limit: int = 10) -> Dict[str, Any]:
        """Search for packages with a specific version pattern."""
        return self.es_client.search_packages_with_version(query, version_pattern, limit)

    def advanced_query(self, index_type: str, query_string: str, limit: int = 10) -> Dict[str, Any]:
        """Execute an advanced query using Elasticsearch's query string syntax."""
        return self.es_client.advanced_query(index_type, query_string, limit)

    def get_package_stats(self, query: str = "*") -> Dict[str, Any]:
        """Get statistics about NixOS packages."""
        return self.es_client.get_package_stats(query)
