"""Client modules for MCP-NixOS."""

from mcp_nixos.clients.elasticsearch_client import ElasticsearchClient
from mcp_nixos.clients.home_manager_client import HomeManagerClient

__all__ = ["ElasticsearchClient", "HomeManagerClient"]
