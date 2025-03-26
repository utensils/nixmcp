"""
NixMCP - Model Context Protocol server for NixOS and Home Manager resources.

This package provides MCP resources and tools for interacting with NixOS packages,
system options, and Home Manager configuration options.
"""

__version__ = "0.1.2"

# Import main components for easier access
from nixmcp.contexts.nixos_context import NixOSContext
from nixmcp.contexts.home_manager_context import HomeManagerContext
