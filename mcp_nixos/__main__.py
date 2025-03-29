#!/usr/bin/env python
"""
CLI entry point for MCP-NixOS server.
"""

# Import mcp from server
from mcp_nixos.server import mcp

# Expose mcp for entry point script
# This is needed for the "mcp-nixos = "mcp_nixos.__main__:mcp.run" entry point in pyproject.toml

if __name__ == "__main__":
    mcp.run()
