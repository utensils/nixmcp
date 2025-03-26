#!/usr/bin/env python
"""
CLI entry point for NixMCP server.
"""

# Import mcp from server
from nixmcp.server import mcp

# Expose mcp for entry point script
# This is needed for the "nixmcp = "nixmcp.__main__:mcp.run" entry point in pyproject.toml

if __name__ == "__main__":
    mcp.run()
