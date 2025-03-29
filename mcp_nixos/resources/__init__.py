"""Resource modules for MCP-NixOS."""

from mcp_nixos.resources.home_manager_resources import register_home_manager_resources
from mcp_nixos.resources.nixos_resources import register_nixos_resources

__all__ = ["register_nixos_resources", "register_home_manager_resources"]
