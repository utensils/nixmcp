"""Tool modules for MCP-NixOS."""

from mcp_nixos.tools.home_manager_tools import register_home_manager_tools
from mcp_nixos.tools.nixos_tools import register_nixos_tools

__all__ = ["register_nixos_tools", "register_home_manager_tools"]
