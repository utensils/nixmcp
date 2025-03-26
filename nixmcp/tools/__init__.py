"""Tool modules for NixMCP."""

from nixmcp.tools.nixos_tools import register_nixos_tools
from nixmcp.tools.home_manager_tools import register_home_manager_tools

__all__ = ["register_nixos_tools", "register_home_manager_tools"]
