"""Resource modules for NixMCP."""

from nixmcp.resources.nixos_resources import register_nixos_resources
from nixmcp.resources.home_manager_resources import register_home_manager_resources

__all__ = ["register_nixos_resources", "register_home_manager_resources"]
